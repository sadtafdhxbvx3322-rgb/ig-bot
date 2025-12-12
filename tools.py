import requests
import asyncio
from pyrogram import Client
from config import Config
import time
import os
import yt_dlp

# --- 1. MUSIC DOWNLOADER (yt-dlp) ---
def download_media(url, is_audio=False):
    """
    Extracts direct media URL. Returns (URL, Error_Message).
    """
    try:
        # Optimization for Render (No FFmpeg needed for m4a)
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best' if is_audio else 'best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                return None, f"Link Extraction Failed: {str(e)}"
            
            if 'url' in info: return info['url'], None
            if 'entries' in info: return info['entries'][0]['url'], None
            
            return None, "No URL found in video info."

    except Exception as e:
        return None, f"System Error: {str(e)}"

# --- 2. LOCAL FILE SAVER ---
def download_file_locally(url, filename="song.m4a"):
    """
    Downloads file to /tmp for uploading. Returns (Path, Error).
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, stream=True, timeout=20)
        
        if resp.status_code == 200:
            path = f"/tmp/{filename}" if os.path.exists("/tmp") else filename
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return path, None
        else:
            return None, f"Download Status: {resp.status_code}"
            
    except Exception as e:
        return None, f"Write Error: {e}"

# --- 3. TELEGRAM LOOKUP (Safety Timeout) ---
async def run_lookup(number):
    if not Config.SESSION_STRING: 
        return "⚠️ Config Error: Session String Missing."

    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    try:
        async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            for bot in bots:
                try:
                    sent = await app.send_message(bot, number)
                    
                    # Wait MAX 5 seconds then give up (Prevents hanging)
                    await asyncio.sleep(5) 
                    
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id and "start" not in msg.text.lower():
                            return f"🕵️ Result ({bot}):\n{msg.text}"
                except: continue
    except Exception as e:
        return f"❌ Connection Error: {e}"

    return "❌ No Data Found (Bots ignored request)."

def truecaller_lookup(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except Exception as e: 
        return f"❌ Logic Error: {e}"
