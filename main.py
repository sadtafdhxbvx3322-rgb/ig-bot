import os
import time
import json
import logging
import requests
import re
import asyncio
import yt_dlp
import tarfile
import shutil
from flask import Flask
from instagrapi import Client
from pyrogram import Client as TGClient
from config import Config

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore', 'yt_dlp']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online (FFmpeg Enabled)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================== 0. FFMPEG INSTALLER (The Magic Fix) ==================
def install_ffmpeg():
    """
    Downloads and installs FFmpeg automatically on Render.
    This fixes the 'Invalid File Format' error for Voice Notes.
    """
    ffmpeg_path = "/tmp/ffmpeg"
    if os.path.exists(f"{ffmpeg_path}/ffmpeg"):
        # Add to PATH so instagrapi can find it
        os.environ["PATH"] += os.pathsep + ffmpeg_path
        print("✅ FFmpeg already installed.")
        return

    print("⬇️ Installing FFmpeg (Crucial for Voice Notes)...")
    try:
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = "/tmp/ffmpeg.tar.xz"
        
        # Download
        resp = requests.get(url, stream=True)
        with open(tar_path, 'wb') as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)
        
        # Extract
        print("📦 Extracting FFmpeg...")
        with tarfile.open(tar_path) as tar:
            tar.extractall("/tmp")
        
        # Find the extracted folder name (it changes with version)
        extracted_folder = [f for f in os.listdir("/tmp") if "ffmpeg-" in f and os.path.isdir(f"/tmp/{f}")][0]
        
        # Move binary to clean path
        if not os.path.exists(ffmpeg_path):
            os.makedirs(ffmpeg_path)
        shutil.move(f"/tmp/{extracted_folder}/ffmpeg", f"{ffmpeg_path}/ffmpeg")
        shutil.move(f"/tmp/{extracted_folder}/ffprobe", f"{ffmpeg_path}/ffprobe")
        
        # Add to System PATH
        os.environ["PATH"] += os.pathsep + ffmpeg_path
        
        # Cleanup
        os.remove(tar_path)
        print("✅ FFmpeg Installed Successfully!")
        
    except Exception as e:
        print(f"⚠️ FFmpeg Install Failed: {e}")

# ================== 1. SMART AI ==================
def ask_ai(text):
    try:
        system = "Reply in the same language as user. Be helpful and short."
        prompt = f"{system}\nUser: {text}"
        url = f"https://text.pollinations.ai/{prompt}"
        return requests.get(url, timeout=10).text.strip()
    except: return None

# ================== 2. MUSIC DOWNLOADER ==================
def download_music(query):
    try:
        clean_query = query.lower().replace("play ", "").strip()
        print(f"🎵 Searching: {clean_query}")
        
        filename = f"song_{int(time.time())}.m4a"
        path = f"/tmp/{filename}"
        if os.path.exists(path): os.remove(path)

        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best',
            'outtmpl': path,
            'default_search': 'scsearch1', # SoundCloud
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean_query])

        if os.path.exists(path): return path, None
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
    # Step 0: Install FFmpeg First!
    install_ffmpeg()
    
    print("🚀 Starting FINAL BOT...")

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
                num_match = re.search(r'(\+?\d{10,})', text)
                if num_match:
                    phone = num_match.group(1)
                    cl.direct_answer(tid, f"🕵️ Checking {phone}...")
                    res = search_number(phone)
                    cl.direct_answer(tid, res)

                # --- B. MUSIC (Voice Note) ---
                elif "play " in text.lower():
                    cl.direct_answer(tid, "🔍 Searching...")
                    path, err = download_music(text)
                    
                    if path:
                        cl.direct_answer(tid, "🚀 Uploading Voice Note...")
                        try:
                            # Ab FFmpeg hai, toh 'waveform' fake dene ki zarurat nahi, 
                            # lekin speed ke liye fake rakh sakte hain.
                            # Hum real processing hone denge taaki format sahi rahe.
                            cl.direct_send_voice(path, [t.users[0].pk])
                            cl.direct_answer(tid, "✅ Sent.")
                        except Exception as e:
                            print(f"VN Error: {e}")
                            # Agar VN fail hua, toh File bhejo (Fallback)
                            try:
                                cl.direct_send_file(path, [t.users[0].pk])
                                cl.direct_answer(tid, "✅ Sent as Audio File (VN Failed).")
                            except Exception as e2:
                                cl.direct_answer(tid, f"❌ Upload Error: {e2}")
                        finally:
                            if os.path.exists(path): os.remove(path)
                    else:
                        cl.direct_answer(tid, "❌ Song not found.")

                # --- C. SMART AI ---
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
