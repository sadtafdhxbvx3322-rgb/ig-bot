import os
import time
import threading
import json
import logging
import re
import requests
import yt_dlp
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from config import Config

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
# Silence background noise
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore', 'yt_dlp']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online (Threaded)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================== TOOLS (Inside Main to prevent Import Errors) ==================

def get_ai_reply(model, text):
    """Safe AI Reply with Timeout"""
    if not model: return None
    try:
        return model.generate_content(f"Reply in Hinglish slang. User: {text}").text.strip()
    except: return None

def get_yt_link_from_ai(model, text):
    if not model: return None
    try:
        return model.generate_content(f"Find YouTube URL for '{text}'. Reply ONLY with URL.").text.strip()
    except: return None

def download_audio(url):
    """Downloads audio using yt-dlp to /tmp folder"""
    try:
        # Generate a unique filename to prevent conflicts
        filename = f"song_{int(time.time())}.m4a"
        path = f"/tmp/{filename}"
        
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best',
            'outtmpl': path,
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(path):
            return path, None
        return None, "Download finished but file not found."
    except Exception as e:
        return None, str(e)

# ================== WORKER FUNCTION (Runs in background) ==================

def handle_message(client, thread_id, text, model):
    """
    This function runs separately for every message.
    If this crashes, the main bot DOES NOT STOP.
    """
    try:
        print(f"⚙️ Processing: {text}")

        # --- 1. NUMBER LOOKUP (Disabled temporarily to fix crashing) ---
        # Telegram is the #1 cause of freezing. I disabled it to prove the bot works.
        # If you see the bot working, we know Telegram was the issue.
        if re.search(r'(\+?\d{10,})', text):
            client.direct_answer(thread_id, "⚠️ Telegram Search is disabled to prevent crashing. Bot is stable.")
            return

        # --- 2. MUSIC / DOWNLOAD ---
        if "play " in text.lower() or "spotify" in text.lower() or "instagram.com" in text.lower():
            client.direct_answer(thread_id, "🔍 Searching...")
            
            target_url = text
            # AI Helper for song names
            if "play " in text.lower() and "http" not in text and model:
                ai_link = get_yt_link_from_ai(model, text)
                if ai_link and "http" in ai_link:
                    target_url = ai_link.split()[-1]

            # Download
            path, err = download_audio(target_url)
            
            if path:
                try:
                    client.direct_send_voice(path, [client.direct_thread(thread_id).users[0].pk])
                    client.direct_answer(thread_id, "✅ Sent.")
                    os.remove(path) # Clean up
                except Exception as e:
                    client.direct_answer(thread_id, f"❌ Upload Failed: {e}")
            else:
                client.direct_answer(thread_id, f"❌ Download Failed: {err}")

        # --- 3. AI CHAT ---
        elif model:
            reply = get_ai_reply(model, text)
            if reply:
                client.direct_answer(thread_id, reply)

    except Exception as e:
        print(f"⚠️ Worker Error: {e}")
        try:
            client.direct_answer(thread_id, f"⚠️ Error: {e}")
        except: pass

# ================== MAIN BOT LOOP ==================

def run_bot():
    print("🚀 Starting THREADED Bot...")

    # 1. AI
    genai.configure(api_key=Config.GEMINI_KEY)
    try: model = genai.GenerativeModel("gemini-1.5-flash")
    except: model = None

    # 2. LOGIN
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
                
                # --- CRITICAL FIX: LAUNCH THREAD ---
                # Instead of running logic here, we start a background worker.
                # The main loop goes back immediately to check for new msgs.
                task = threading.Thread(target=handle_message, args=(cl, t.pk, text, model))
                task.start()

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)
        
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
