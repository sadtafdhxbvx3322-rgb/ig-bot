import os
import time
import json
import logging
import requests
import yt_dlp
from flask import Flask
from instagrapi import Client
from config import Config

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore', 'yt_dlp']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online (Unlimited Mode)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================== 1. UNLIMITED AI (Pollinations) ==================
def ask_pollinations(text):
    """
    Uses Pollinations.ai (Free/No Key) to generate replies.
    Never gives 429/404 errors.
    """
    try:
        # Construct prompt for Hinglish slang
        prompt = f"Reply to this user message in cool Indian Hinglish slang (Bro/Yaar style). Keep it short. Message: {text}"
        # URL encode is handled by requests usually, but direct string works for simple cases
        url = f"https://text.pollinations.ai/{prompt}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        print(f"AI Fail: {e}")
    return "Arre bro, network issue hai. Thodi der mein bolta hoon!"

# ================== 2. SEARCH & DOWNLOAD ENGINE ==================
def download_song(query):
    """
    Searches YouTube for 'query' and downloads audio.
    Returns: (FilePath, ErrorMessage)
    """
    try:
        # Clean the query (remove "play")
        search_term = query.lower().replace("play ", "").strip()
        print(f"🔍 Searching YouTube for: {search_term}")
        
        filename = f"song_{int(time.time())}.m4a"
        path = f"/tmp/{filename}"
        if os.path.exists(path): os.remove(path)

        # 'ytsearch1:' tells yt-dlp to SEARCH and pick the first result
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best',
            'outtmpl': path,
            'default_search': 'ytsearch1',  # <--- CRITICAL FIX
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([search_term])

        if os.path.exists(path):
            return path, None
        else:
            return None, "Download finished but file missing."

    except Exception as e:
        return None, str(e)

# ================== MAIN LOGIC ==================
def run_bot():
    print("🚀 Starting UNLIMITED Bot...")

    # 1. LOGIN
    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        my_id = str(cl.user_id)
        print(f"✅ Login Success: {my_id}")
    except Exception as e:
        print(f"❌ Login Failed: {e}")
        return

    print("👀 Watching messages...")
    processed = set()

    while True:
        try:
            threads = cl.direct_threads(amount=5)

            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                
                if msg.id in processed: continue
                if str(msg.user_id) == my_id: continue

                processed.add(msg.id)
                text = getattr(msg, 'text', "").strip()
                if not text: continue
                
                print(f"📩 New Task: {text}")
                tid = t.pk

                # --- FEATURE 1: MUSIC (Play ...) ---
                if "play " in text.lower() or "spotify" in text.lower():
                    try:
                        cl.direct_answer(tid, f"🔍 Searching '{text}'...")
                        
                        # Download using Search Mode
                        path, err = download_song(text)
                        
                        if path:
                            cl.direct_answer(tid, "🚀 Uploading Voice Note...")
                            cl.direct_send_voice(path, [t.users[0].pk])
                            cl.direct_answer(tid, "✅ Sent.")
                            os.remove(path)
                        else:
                            cl.direct_answer(tid, f"❌ Error: {err}")
                            
                    except Exception as e:
                        cl.direct_answer(tid, f"⚠️ Music Crash: {e}")

                # --- FEATURE 2: AI CHAT (Normal Msgs) ---
                else:
                    try:
                        # Use Pollinations (No Keys, No Limits)
                        reply = ask_pollinations(text)
                        if reply:
                            cl.direct_answer(tid, reply)
                    except Exception as e:
                        print(f"Chat Error: {e}")

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)
        
        time.sleep(5)

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
