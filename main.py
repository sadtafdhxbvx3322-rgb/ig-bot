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

# --- DEBUG LOGGING (Show EVERYTHING) ---
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- STATUS TRACKER ---
bot_status = {"ai_active": False, "model_name": "None", "errors": 0}

@app.route('/')
def home():
    return f"Bot Online. AI: {bot_status['model_name']}."

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🚀 Starting DEBUG Bot...")

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
    print("🐞 DEBUG MODE: ON (Errors will be sent to Chat)")
    processed_msg_ids = set() 

    while True:
        try:
            threads = cl.direct_threads(amount=3)

            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                msg_id = msg.id
                
                if msg_id in processed_msg_ids: continue
                if str(msg.user_id) == my_id: continue

                processed_msg_ids.add(msg_id) 
                
                text = getattr(msg, 'text', "")
                uid = t.users[0].pk
                thread_id = t.pk
                
                print(f"📩 {uid}: {text}")

                try:
                    safe_text = text if text else ""
                    
                    # 1. Music / Download
                    if "play " in safe_text.lower() or "spotify" in safe_text or "instagram.com" in safe_text:
                        cl.direct_answer(thread_id, "🔍 Debugging Download...")
                        
                        target = safe_text
                        if "play " in safe_text.lower() and "http" not in safe_text and model:
                            try:
                                prompt = f"Find YouTube URL for: '{safe_text}'. Reply ONLY with URL."
                                ai_resp = model.generate_content(prompt).text.strip()
                                target = ai_resp.split()[-1] if "http" in ai_resp else ai_resp
                                cl.direct_answer(thread_id, f"📝 AI Found URL: {target}")
                            except Exception as e:
                                cl.direct_answer(thread_id, f"⚠️ AI Search Error: {e}")

                        # Call Downloader
                        link = download_media(target, "spotify" in safe_text or "play " in safe_text.lower())
                        
                        if link and "http" in link:
                            cl.direct_answer(thread_id, f"✅ Link:\n{link}")
                        else:
                            # Send the EXACT error reason from tools.py
                            cl.direct_answer(thread_id, f"❌ Download Failed. Reason:\n{link}")

                    # 2. AI Chat
                    elif model:
                        try:
                            prompt = f"Reply in Hinglish. User: {safe_text}"
                            reply = model.generate_content(prompt).text.strip()
                            cl.direct_answer(thread_id, reply)
                            
                            # Database Check
                            try:
                                save_interaction(uid, safe_text, reply)
                            except Exception as db_e:
                                # Tell user DB is failing
                                cl.direct_answer(thread_id, f"⚠️ Reply sent, but DB Error: {db_e}")
                                
                        except Exception as ai_e:
                            cl.direct_answer(thread_id, f"⚠️ AI Generation Error: {ai_e}")

                except Exception as inner_e:
                    error_msg = f"⚠️ Logic Error: {str(inner_e)}"
                    print(error_msg)
                    cl.direct_answer(thread_id, error_msg)
                    traceback.print_exc()

            if len(processed_msg_ids) > 1000:
                processed_msg_ids.clear()

        except Exception as e:
            print(f"🔥 Major Loop Error: {e}")
            time.sleep(5)

        time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
