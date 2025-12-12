import requests
import asyncio
from pyrogram import Client
from config import Config
import time
import os
import yt_dlp

# --- 1. DEBUG DOWNLOADER ---
def download_media(url, is_audio=False):
    """
    Returns a Tuple: (Download_URL, Error_Message)
    """
    try:
        # Debug Options for yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best' if is_audio else 'best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            # User Agent to trick YouTube/Servers
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                return None, f"yt-dlp Extraction Failed: {str(e)}"
            
            if 'url' in info:
                return info['url'], "Success"
            elif 'entries' in info:
                return info['entries'][0]['url'], "Success"
            else:
                return None, "yt-dlp: No URL found in info dict."

    except Exception as e:
        return None, f"System Error: {str(e)}"

# --- 2. LOCAL FILE SAVER ---
def download_file_locally(url, filename="song.mp3"):
    """
    Returns Tuple: (File_Path, Error_Message)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Increased timeout to 30s
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        
        if resp.status_code == 200:
            path = f"/tmp/{filename}" if os.path.exists("/tmp") else filename
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return path, "Success"
        else:
            return None, f"Download Status Code: {resp.status_code}"
            
    except Exception as e:
        return None, f"File Write Error: {str(e)}"

# --- 3. TELEGRAM LOOKUP (Debug) ---
async def run_lookup(number):
    if not Config.SESSION_STRING: 
        return "⚠️ Config Error: Telegram Session String is Missing."

    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]
    debug_log = []

    try:
        async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            
            debug_log.append("✅ TG Client Connected")
            
            for bot in bots:
                try:
                    debug_log.append(f"Trying Bot: {bot}")
                    sent = await app.send_message(bot, number)
                    
                    # Wait 5s
                    await asyncio.sleep(5) 
                    
                    found = False
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id:
                            if "start" not in msg.text.lower():
                                return f"🕵️ Result ({bot}):\n{msg.text}"
                            else:
                                debug_log.append(f"{bot} replied with Start menu (Failed).")
                            found = True
                    
                    if not found:
                        debug_log.append(f"{bot} did not reply.")

                except Exception as inner_e:
                    debug_log.append(f"{bot} Error: {inner_e}")
                    continue

    except Exception as e:
        return f"❌ TG Connect Error: {e}"

    return "❌ Lookup Failed.\nDebug Log:\n" + "\n".join(debug_log)

def truecaller_lookup(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except Exception as e: 
        return f"❌ System Loop Error: {e}"
