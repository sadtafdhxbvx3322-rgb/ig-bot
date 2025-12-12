import os
import time
import json
import logging
import requests
import re
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
def home(): return "Bot Online (Smart AI Mode)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================== 1. SMART AI (No Cringe Slang) ==================
def ask_ai(text):
    """
    Uses Pollinations AI but with a strictly 'Helpful & Adaptive' persona.
    """
    try:
        # --- NEW PROMPT STRATEGY ---
        # Ye prompt bot ko force karega ki wo tumhari language match kare.
        system_instruction = (
            "You are a helpful and smart Instagram assistant. "
            "IMPORTANT: Reply in the SAME LANGUAGE as the user. "
            "If the user speaks English, reply in normal English. "
            "If the user speaks Hindi/Hinglish, reply in Hinglish. "
            "Do NOT use excessive slang like 'chill maar' or 'kya scene hai' unless the user does. "
            "Keep replies short, logical, and directly answer the question."
        )
        
        prompt = f"{system_instruction}\n\nUser Message: {text}"
        url = f"https://text.pollinations.ai/{prompt}"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.text.strip()
            
    except Exception as e:
        print(f"AI Error: {e}")
    
    return "I didn't get that. Could you say it again?"

# ================== 2. MUSIC DOWNLOADER (SoundCloud) ==================
def download_music(query):
    try:
        clean_query = query.lower().replace("play ", "").strip()
        print(f"🎵 Searching SoundCloud: {clean_query}")
        
        filename = f"song_{int(time.time())}.mp3"
        path = f"/tmp/{filename}"
        if os.path.exists(path): os.remove(path)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': path,
            'default_search': 'scsearch1', # SoundCloud Search
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean_query])

        if os.path.exists(path): return path, None
        return None, "Song not found."

    except Exception as e:
        return None, str(e)

# ================== MAIN BOT ==================
def run_bot():
    print("🚀 Starting SMART BOT...")

    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        print(f"✅ Login Success: {cl.user_id}")
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
                
                if msg.id in processed or str(msg.user_id) == str(cl.user_id): continue
                processed.add(msg.id)

                text = getattr(msg, 'text', "").strip()
                if not text: continue
                
                print(f"📩 Msg: {text}")
                tid = t.pk

                # --- A. MUSIC ---
                if "play " in text.lower():
                    cl.direct_answer(tid, "🔍 Searching SoundCloud...")
                    path, err = download_music(text)
                    
                    if path:
                        cl.direct_answer(tid, "🚀 Uploading Voice Note...")
                        try:
                            cl.direct_send_voice(path, [t.users[0].pk])
                            cl.direct_answer(tid, "✅ Sent.")
                            os.remove(path)
                        except:
                            cl.direct_answer(tid, "❌ Upload Failed.")
                    else:
                        cl.direct_answer(tid, "❌ Song not found.")

                # --- B. NUMBER SEARCH ---
                elif re.search(r'(\+?\d{10,})', text):
                     cl.direct_answer(tid, "🕵️ Number detected (Telegram disabled for stability).")

                # --- C. SMART AI CHAT ---
                else:
                    reply = ask_ai(text)
                    if reply: cl.direct_answer(tid, reply)

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)
        
        time.sleep(5)

if __name__ == "__main__":
    import threading
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
