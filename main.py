import os
import time
import json
import logging
import requests
import re
import shutil
import tarfile
import subprocess
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
def home(): return "Bot Online (FFmpeg + FFprobe Fixed)"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# ================== 0. FULL MEDIA TOOLS INSTALLER ==================
def setup_media_tools():
    """
    Downloads BOTH FFmpeg and FFprobe. 
    This is required because Instagrapi needs ffprobe to analyze audio.
    """
    bin_dir = os.path.join(os.getcwd(), "bin")
    ffmpeg_exe = os.path.join(bin_dir, "ffmpeg")
    ffprobe_exe = os.path.join(bin_dir, "ffprobe")

    # 1. Check if both exist
    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        print("✅ FFmpeg & FFprobe already installed.")
        os.environ["PATH"] += os.pathsep + bin_dir
        return

    print("⬇️ Downloading Media Tools (FFmpeg + FFprobe)...")
    try:
        if os.path.exists(bin_dir): shutil.rmtree(bin_dir)
        os.makedirs(bin_dir)

        # Download Static Build (Contains both tools)
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = "tools.tar.xz"
        
        resp = requests.get(url, stream=True)
        with open(tar_path, 'wb') as f:
            for chunk in resp.iter_content(4096):
                f.write(chunk)
        
        # Extract
        print("📦 Extracting...")
        with tarfile.open(tar_path) as tar:
            tar.extractall(path=bin_dir)
        
        # Locate the inner folder (name changes with version)
        inner_folder = [f for f in os.listdir(bin_dir) if "ffmpeg-" in f and os.path.isdir(os.path.join(bin_dir, f))][0]
        source_dir = os.path.join(bin_dir, inner_folder)

        # Move binaries to main bin folder
        shutil.move(os.path.join(source_dir, "ffmpeg"), ffmpeg_exe)
        shutil.move(os.path.join(source_dir, "ffprobe"), ffprobe_exe)
        
        # CRITICAL: Grant Permissions to BOTH
        os.chmod(ffmpeg_exe, 0o755)
        os.chmod(ffprobe_exe, 0o755)
        
        # Add to Path
        os.environ["PATH"] += os.pathsep + bin_dir
        
        # Verify
        subprocess.run([ffmpeg_exe, "-version"], stdout=subprocess.DEVNULL, check=True)
        subprocess.run([ffprobe_exe, "-version"], stdout=subprocess.DEVNULL, check=True)
        print("✅ Media Tools Installed & Verified!")
        
        # Cleanup
        if os.path.exists(tar_path): os.remove(tar_path)
        shutil.rmtree(source_dir)
        
    except Exception as e:
        print(f"❌ Install Failed: {e}")

# ================== 1. SMART AI ==================
def ask_ai(text):
    try:
        prompt = f"Reply in the same language as the user. Keep it helpful and short. User: {text}"
        url = f"https://text.pollinations.ai/{prompt}"
        return requests.get(url, timeout=10).text.strip()
    except: return None

# ================== 2. MUSIC DOWNLOADER ==================
def download_music(query):
    try:
        clean_query = query.lower().replace("play ", "").strip()
        print(f"🎵 Searching: {clean_query}")
        
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

# ================== MAIN BOT ==================
def run_bot():
    # Step 1: Install FFmpeg AND FFprobe
    setup_media_tools()

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

                # --- MUSIC (VOICE NOTE) ---
                if "play " in text.lower():
                    cl.direct_answer(tid, "🔍 Searching...")
                    path, err = download_music(text)
                    
                    if path:
                        cl.direct_answer(tid, "🚀 Uploading Voice Note...")
                        try:
                            # Now that we have FFprobe, this will work!
                            cl.direct_send_voice(path, [t.users[0].pk])
                            cl.direct_answer(tid, "✅ Sent.")
                        except Exception as e:
                            print(f"VN Error: {e}")
                            # Final Safety Net
                            cl.direct_answer(tid, f"❌ Voice Note Failed: {e}\n(Try again in 1 min)")
                        finally:
                            if os.path.exists(path): os.remove(path)
                    else:
                        cl.direct_answer(tid, "❌ Song not found.")

                # --- AI CHAT ---
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
