import os
import time
import threading
import json
import logging
import requests
from flask import Flask
from instagrapi import Client
from tools import download_media, truecaller_lookup
from config import Config

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online (Pollinations AI)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# --- NEW: Pollinations AI (Free & No Limits) ---
def ask_ai(prompt):
    """
    Uses Pollinations.ai API (No Key Required).
    """
    try:
        # We use 'search' mode false to get direct chat
        url = f"https://text.pollinations.ai/{prompt}"
        # Adding a model hint (Optional, defaults to GPT-4o-mini usually)
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"⚠️ AI Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ AI Connection Failed: {e}")
        return None

def run_bot():
    print("🚀 Starting Bot with Pollinations AI (Unlimited)...")

    # 1. INSTAGRAM LOGIN
    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        my_id = str(cl.user_id)
        print(f"✅ Login Success. ID: {my_id}")
    except Exception as e:
        print(f"🚨 Login Failed: {e}")
        return

    # 2. MAIN LOOP
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
                        if "play " in safe_text.lower() and "http" not in safe_text:
                            # Use Pollinations AI to find song URL
                            ai_prompt = f"Find YouTube Music URL for song: '{safe_text}'. Reply ONLY with the URL. Do not write anything else."
                            ai_resp = ask_ai(ai_prompt)
                            if ai_resp and "http" in ai_resp:
                                target = ai_resp.split()[-1]

                        link = download_media(target, "spotify" in safe_text or "play " in safe_text.lower())
                        
                        if link:
                            cl.direct_answer(thread_id, f"✅ Link:\n{link}")
                        else:
                            cl.direct_answer(thread_id, "❌ Could not download.")

                    # 2. AI Chat (The Default)
                    else:
                        # Direct Chat via Pollinations
                        prompt = f"Reply in Hinglish (Indian slang). User: {safe_text}"
                        reply = ask_ai(prompt)
                        
                        if reply:
                            cl.direct_answer(thread_id, reply)

                except Exception as inner_e:
                    print(f"⚠️ Task Failed: {inner_e}")

            if len(processed_msg_ids) > 1000:
                processed_msg_ids.clear()

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)

        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
