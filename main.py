import os
import time
import json
import logging
import requests
import re
import shutil
import subprocess
import yt_dlp
import imageio_ffmpeg
from flask import Flask
from instagrapi import Client
from pyrogram import Client as TGClient
from config import Config

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
# Clean up logs
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore', 'yt_dlp']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online (VN Force Fix)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================== 0. FFMPEG ENFORCER ==================
def setup_ffmpeg():
    """
    Finds the FFmpeg binary from the library and FORCES it to be executable.
    """
    try:
        # 1. Get path from library
        ffmpeg_bin_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"📍 FFmpeg binary found at: {ffmpeg_bin_path}")

        # 2. Force Executable Permissions (Crucial for Render)
        try:
            os.chmod(ffmpeg_bin_path, 0o755)
            print("✅ Permissions updated to 755 (Executable).")
        except Exception as e:
            print(f"⚠️ Could not change permissions: {e}")

        # 3. Add directory to System PATH
        ffmpeg_dir = os.path.dirname(ffmpeg_bin_path)
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        
        # 4. TEST IT
        # If this passes, Voice Notes WILL work.
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("✅ FFmpeg System Test: PASSED")
        else:
            print("❌ FFmpeg System Test: FAILED")
            
    except Exception as e:
        print(f"❌ FFmpeg Setup Critical Fail: {e}")

# ================== 1. SMART AI ==================
def ask_ai(text):
    try:
        system = "Reply in the same language as the user. Keep it helpful and short."
        prompt = f"{system}\nUser: {text}"
        url = f"https://text.pollinations.ai/{prompt}"
        return requests.get(url, timeout=10).text.strip()
    except: return None

# ================== 2. MUSIC DOWNLOADER ==================
def download_music(query):
    try:
        clean_query = query.lower().replace("play ", "").strip()
        print(f"🎵 Searching: {clean_query}")
        
        # Instagrapi expects M4A for best compatibility
        filename = f"song_{int(time.time())}.m4a"
        path = os.path.join(os.getcwd(), filename)
        
        if os.path.exists(path): os.remove(path)

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best',
            'outtmpl': path,
            'default_search': 'scsearch1', # SoundCloud
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean_query])

        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path, None
        return None, "Song not found."
    except Exception as e: return None, str(e)

# ================== 3. TELEGRAM SEARCH ==================
async def run_tg_search(number):
    if not Config.SESSION_STRING: return "⚠️ Config Missing"
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]
    try:
        async with TGClient("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            for bot in bots:
                try:
                    sent = await app.send_message(bot, number)
                    await asyncio.sleep(5)
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id and "start" not in msg.text.lower():
                            return f"🕵️ Info ({bot}):\n{msg.text}"
                except: continue
    except Exception as e: return f"❌ TG Error: {e}"
    return "❌ No Data Found."

def search_number(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_tg_search(n))
        loop.close()
        return res
    except: return "❌ System Error"

# ================== MAIN BOT ==================
def run_bot():
    # Step 1: Force FFmpeg
    setup_ffmpeg()

    print("🚀 Starting INSTA BOT...")
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

                # --- A. NUMBER SEARCH ---
                if re.search(r'(\+?\d{10,})', text):
                    phone = re.search(r'(\+?\d{10,})', text).group(1)
                    cl.direct_answer(tid, f"🕵️ Checking {phone}...")
                    cl.direct_answer(tid, search_number(phone))

                # --- B. MUSIC (VOICE NOTE ONLY) ---
                elif "play " in text.lower():
                    cl.direct_answer(tid, "🔍 Searching...")
                    path, err = download_music(text)
                    
                    if path:
                        cl.direct_answer(tid, "🚀 Uploading Voice Note...")
                        try:
                            # 1. Try sending as proper Voice Note
                            # We pass fake waveform/duration to speed it up and skip internal probe if possible
                            cl.direct_send_voice(path, [t.users[0].pk], waveform=[0]*100, duration_ms=30000)
                            cl.direct_answer(tid, "✅ Sent.")
                        except Exception as e:
                            print(f"VN Error: {e}")
                            # 2. If that fails, send as AUDIO FILE (Not a link, actual file)
                            try:
                                cl.direct_send_file(path, [t.users[0].pk])
                                cl.direct_answer(tid, "✅ Sent as Audio File.")
                            except Exception as e2:
                                cl.direct_answer(tid, f"❌ Critical Upload Error: {e2}")
                        finally:
                            if os.path.exists(path): os.remove(path)
                    else:
                        cl.direct_answer(tid, "❌ Song not found.")

                # --- C. AI CHAT ---
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
