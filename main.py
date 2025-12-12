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
# from database import get_user_memory, save_interaction # DISABLED FOR SAFETY
from config import Config

# --- DEBUG LOGS ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🚀 Starting SAFE MODE Bot...")

    # 1. AI SETUP
    genai.configure(api_key=Config.GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("✅ AI Connected")

    # 2. INSTAGRAM LOGIN
    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        my_id = str(cl.user_id)
        print(f"✅ Login Success. My ID: {my_id}")
    except Exception as e:
        print(f"🚨 LOGIN CRASH: {e}")
        return

    # 3. MAIN LOOP
    print("👀 Watching for messages...")
    processed_ids = set()

    while True:
        try:
            # Fetch latest threads
            threads = cl.direct_threads(amount=5)

            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                
                # SKIP if already processed
                if msg.id in processed_ids: continue
                
                # SKIP if message is from ME (The Bot)
                if str(msg.user_id) == my_id:
                    # print(f"Skipping my own msg: {msg.text[:10]}")
                    continue

                # NEW MESSAGE DETECTED
                processed_ids.add(msg.id)
                text = msg.text
                print(f"📩 New Msg: {text}")

                # --- REPLY LOGIC ---
                try:
                    # 1. Music / Play
                    if "play " in text.lower() or "spotify" in text or "instagram.com" in text:
                        cl.direct_answer(t.pk, "🔍 Finding media...")
                        target = text
                        
                        # AI Clean up
                        if "play " in text.lower() and "http" not in text:
                            try:
                                prompt = f"Find YouTube URL for: '{text}'. Reply ONLY with URL."
                                target = model.generate_content(prompt).text.strip()
                            except: pass
                        
                        link = download_media(target, "spotify" in text or "play " in text.lower())
                        
                        if link and "http" in link:
                            cl.direct_answer(t.pk, f"✅ Download:\n{link}")
                        else:
                            cl.direct_answer(t.pk, f"❌ Failed: {link}") # Shows error reason

                    # 2. Chat (AI)
                    else:
                        prompt = f"Reply in Hinglish (Indian slang). User: {text}"
                        reply = model.generate_content(prompt).text.strip()
                        cl.direct_answer(t.pk, reply)
                        print(f"🗣️ Replied: {reply}")

                except Exception as e:
                    cl.direct_answer(t.pk, f"⚠️ Error: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)
            
        time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
