import requests
import asyncio
from pyrogram import Client
from config import Config
import time
import os
import yt_dlp # Direct YouTube Library

# --- 1. DIRECT DOWNLOADER (Using yt-dlp) ---
def download_media(url, is_audio=False):
    """
    Uses yt-dlp to extract media URL directly from YouTube/Instagram/etc.
    Bypasses Cobalt/External APIs completely.
    """
    try:
        # Options for yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best' if is_audio else 'best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            # Render ke liye geo-bypass options
            'geo_bypass': True,
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get the direct download URL
            if 'url' in info:
                return info['url']
            elif 'entries' in info:
                # Sometimes it returns a playlist object for single video
                return info['entries'][0]['url']
            else:
                return None

    except Exception as e:
        print(f"⚠️ yt-dlp Error: {e}")
        return None

# --- 2. LOCAL FILE SAVER ---
def download_file_locally(url, filename="song.mp3"):
    """Downloads audio to temp folder for upload."""
    try:
        # User-Agent lagana zaroori hai nahi toh Google block kar dega
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, stream=True, timeout=20)
        if resp.status_code == 200:
            path = f"/tmp/{filename}" if os.path.exists("/tmp") else filename
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return path
    except Exception as e:
        print(f"⚠️ Local Save Error: {e}")
    return None

# --- 3. TELEGRAM LOOKUP (Timeout Fix) ---
async def run_lookup(number):
    if not Config.SESSION_STRING: 
        return "⚠️ Error: Telegram Session String Missing in Config."

    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    try:
        async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            for bot in bots:
                try:
                    sent = await app.send_message(bot, number)
                    await asyncio.sleep(5) # Wait for reply
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id and "start" not in msg.text.lower():
                            return f"🕵️ Info ({bot}):\n{msg.text}"
                except: continue
    except Exception as e:
        if "401" in str(e) or "Auth" in str(e):
            return "❌ Session Expired. Regenerate String."
        return f"❌ TG Connect Error: {e}"

    return "❌ No Data Found."

def truecaller_lookup(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except: return "❌ System Loop Error"
