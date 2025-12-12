import requests
import asyncio
from pyrogram import Client
from config import Config
import time
import random
import os

def download_media(url, is_audio=False):
    """
    Returns the DIRECT URL of the media using Cobalt.
    """
    # 2025 Working Mirrors
    instances = [
        "https://api.cobalt.tools/api/json",       # Official (Best)
        "https://cobalt.arms.nu/api/json",         # Backup 1
        "https://api.server.cobalt.tools/api/json" # Backup 2
    ]
    random.shuffle(instances)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://cobalt.tools",
        "Referer": "https://cobalt.tools/"
    }
    
    payload = {
        "url": url, 
        "vQuality": "720", 
        "filenamePattern": "classic",
        "disableMetadata": True
    }

    if is_audio: 
        payload.update({"isAudioOnly": "true", "aFormat": "mp3"})

    for base_url in instances:
        try:
            resp = requests.post(base_url, json=payload, headers=headers, timeout=15)
            if resp.status_code != 200: continue
            
            data = resp.json()
            # Try to find the direct link
            if "url" in data: return data["url"]
            if "picker" in data: return data["picker"][0]["url"]
            if "audio" in data: return data["audio"]
            
        except: continue

    return None

def download_file_locally(url, filename="temp_audio.mp3"):
    """
    Downloads a file to the local system (required for Voice Note upload).
    """
    try:
        resp = requests.get(url, stream=True)
        if resp.status_code == 200:
            path = f"/tmp/{filename}" if os.path.exists("/tmp") else filename
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return path
    except Exception as e:
        print(f"⚠️ Download Local Failed: {e}")
    return None

async def run_lookup(number):
    if not Config.SESSION_STRING: return "⚠️ Telegram Config Missing"
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    try:
        async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            for bot in bots:
                try:
                    sent = await app.send_message(bot, number)
                    await asyncio.sleep(4) 
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id:
                            return f"🕵️ Info ({bot}):\n{msg.text}"
                except: continue
    except Exception as e:
        return f"❌ TG Error: {e}"
    return "❌ No Response."

def truecaller_lookup(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except: return "❌ System Error"
