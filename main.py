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
# from database import get_user_memory, save_interaction # DB Disabled for stability
from config import Config

# Quiet Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# --- NEW: Smart Model Selector (Fixes 404) ---
def get_working_model():
    """
    Asks Google for available models and picks the best one automatically.
    """
    try:
        print("🔎 Scanning for valid AI models...")
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
        
        if not valid_models:
            print("❌ No AI models found for this Key.")
            return None

        # Priority Selection: Flash -> Pro -> 1.5 -> Any
        chosen = next((m for m in valid_models if 'flash' in m), None)
        if not chosen:
            chosen = next((m for m in valid_models if 'gemini-1.5' in m), None)
        if not chosen:
            chosen = next((m for m in valid_models if 'pro' in m), None)
        if not chosen:
            chosen = valid_models[0]

        print(f"✅ Auto-Selected Model: {chosen}")
        return genai.GenerativeModel(chosen)

    except Exception as e:
        print(f"⚠️ Model Scan Failed: {e}. Trying default 'gemini-pro'...")
        return genai.GenerativeModel("gemini-pro")

def ask_ai(model, prompt):
    """
    Safe AI Asker with Retry Logic
    """
    if not model: return None
    for attempt in range(3):
        try:
            return model.generate_content(prompt).text.strip()
        except Exception as e:
            if "429" in str(e): # Quota Limit
                time.sleep(5)
            elif "404" in str(e): # Model not found mid-run
                return "AI Model Error. Please restart bot."
            else:
                return None
    return "Server Busy. Try later."

def run_bot():
    print("🚀 Starting FINAL Auto-Healing Bot...")

    # 1. AI SETUP (With Auto-Fix)
    genai.configure(api_key=Config.GEMINI_KEY)
    model = get_working_model()

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
    print("⚡ Bot Active (Polling 5s)...")
    processed_msg_ids = set() 

    while True:
        try:
            threads = cl.direct_threads(amount=3)

            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                
                if msg.id in processed_msg_ids: continue
                if str(msg.user_id) == my_id: continue

                processed_msg_ids.add(msg.id) 
                
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
                        if "play " in safe_text.lower() and "http" not in safe_text and model:
                            ai_url = ask_ai(model, f"Find YouTube URL for: '{safe_text}'. Reply ONLY with URL.")
                            if ai_url and "http" in ai_url:
                                target = ai_url.split()[-1]

                        link = download_media(target, "spotify" in safe_text or "play " in safe_text.lower())
                        
                        if link:
                            cl.direct_answer(thread_id, f"✅ Link:\n{link}")
                        else:
                            cl.direct_answer(thread_id, "❌ Could not download.")

                    # 2. AI Chat
                    elif model:
                        reply = ask_ai(model, f"Reply in Hinglish (Indian slang). User: {safe_text}")
                        if reply:
                            cl.direct_answer(thread_id, reply)

                except Exception as inner_e:
                    print(f"⚠️ Task Failed: {inner_e}")

            if len(processed_msg_ids) > 1000:
                processed_msg_ids.clear()

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(10)

        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
