import os
import time
import threading
import json
import logging
import traceback
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from tools import download_media, truecaller_lookup
from database import get_user_memory, save_interaction
from config import Config

# --- LOGGING SETUP (Silence the spam) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

# --- STATUS TRACKER ---
bot_status = {"ai_active": False, "model_name": "None", "errors": 0}

@app.route('/')
def home():
    return f"Bot Online. AI: {bot_status['model_name']}."

def run_web():
    # 0.0.0.0 is crucial for Render/Replit
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🚀 Starting FASTER Auto-Healing Bot...")

    # 1. AI SETUP
    genai.configure(api_key=Config.GEMINI_KEY)
    model = None
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        chosen_model = next((m for m in all_models if 'flash' in m), None) or all_models[0]
        model = genai.GenerativeModel(chosen_model)
        bot_status["ai_active"] = True
        bot_status["model_name"] = chosen_model
        print(f"✅ AI Connected: {chosen_model}")
    except Exception as e:
        print(f"❌ AI Init Failed: {e}")

    # 2. INSTAGRAM LOGIN
    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        my_id = str(cl.user_id)
        print(f"✅ Login Success. ID: {my_id}")
    except Exception as e:
        print(f"🚨 Login Failed: {e}")
        return

    # 3. MAIN LOOP
    print("⚡ Speed Mode: ON (Polling every 3s)")
    processed_msg_ids = set() 

    while True:
        try:
            # Fetch top 3 active threads
            threads = cl.direct_threads(amount=3)

            for t in threads:
                if not t.messages: continue
                
                msg = t.messages[0]
                msg_id = msg.id
                
                # Deduplication & Self-Check (Prevents Loops)
                if msg_id in processed_msg_ids: continue
                if str(msg.user_id) == my_id: continue

                processed_msg_ids.add(msg_id) 
                
                text = getattr(msg, 'text', "")
                uid = t.users[0].pk if t.users else "Unknown"
                thread_id = t.pk
                
                print(f"📩 {uid}: {text}")

                # --- PROCESSING ---
                try:
                    safe_text = text if text else ""
                    
                    # 1. Music / Download
                    if "play " in safe_text.lower() or "spotify" in safe_text or "instagram.com" in safe_text:
                        cl.direct_answer(thread_id, "🔍 Searching...")
                        
                        target = safe_text
                        # AI Music Helper (Extracts song name to URL)
                        if "play " in safe_text.lower() and "http" not in safe_text and model:
                            try:
                                prompt = f"Find the YouTube URL for the song: '{safe_text}'. Reply ONLY with the URL."
                                ai_resp = model.generate_content(prompt).text.strip()
                                target = ai_resp.split()[-1] if "http" in ai_resp else ai_resp
                            except: pass

                        link = download_media(target, "spotify" in safe_text or "play " in safe_text.lower())
                        
                        if link:
                            cl.direct_answer(thread_id, f"✅ Link:\n{link}")
                        else:
                            cl.direct_answer(thread_id, "❌ Could not download. Try a different link.")

                    # 2. Truecaller
                    elif safe_text.startswith("+91") or (safe_text.isdigit() and len(safe_text) > 9):
                        cl.direct_answer(thread_id, "🕵️ Checking...")
                        res = truecaller_lookup(safe_text)
                        cl.direct_answer(thread_id, res)

                    # 3. AI Chat
                    elif model:
                        prompt = f"Reply in Hinglish (Indian slang). User: {safe_text}"
                        reply = model.generate_content(prompt).text.strip()
                        
                        # SEND REPLY
                        cl.direct_answer(thread_id, reply)

                        # SAVE INTERACTION (Silent Fail to prevent 'System Error')
                        try:
                            save_interaction(uid, safe_text, reply)
                        except: pass

                except Exception as e:
                    print(f"⚠️ Error processing msg: {e}")
                    # Only tell user if MAIN logic failed
                    try:
                        cl.direct_answer(thread_id, "⚠️ I'm having a brain freeze (Error)")
                    except: pass

            if len(processed_msg_ids) > 1000:
                processed_msg_ids.clear()

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)

        time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
