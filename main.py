import os
import time
import json
import logging
from flask import Flask
from instagrapi import Client
from config import Config

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/')
def home(): return "Simple Bot Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🚀 Starting SIMPLE TEST Bot...")

    # 1. LOGIN
    cl = Client()
    try:
        # Session load karne ki koshish
        try:
            cl.set_settings(json.loads(Config.INSTA_SESSION))
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        except:
            # Agar session fail ho, toh fresh login
            print("⚠️ Session failed. Trying fresh login...")
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
            
        my_id = str(cl.user_id)
        print(f"✅ Login Success! Bot ID: {my_id}")
    except Exception as e:
        print(f"🔥 LOGIN DEAD: {e}")
        # Agar login fail hua toh yahi ruk jao
        return

    print("👀 Watching messages...")
    processed = set()

    while True:
        try:
            # Threads fetch karo
            threads = cl.direct_threads(amount=5)

            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                
                # Check duplicates & Self
                if msg.id in processed: continue
                if str(msg.user_id) == my_id: continue

                processed.add(msg.id)
                
                text = msg.text
                print(f"📩 Message Recieved: {text}")
                
                # --- BASIC REPLY ---
                try:
                    cl.direct_answer(t.pk, f"✅ Test Successful. I heard: {text}")
                    print("✅ Reply Sent.")
                except Exception as e:
                    print(f"❌ Reply Failed: {e}")

        except Exception as e:
            print(f"⚠️ Loop Error: {e}")
            time.sleep(5)

        time.sleep(5)

if __name__ == "__main__":
    # Web server alag thread mein
    import threading
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
