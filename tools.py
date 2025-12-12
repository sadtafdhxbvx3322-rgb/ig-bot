import requests
import asyncio
from pyrogram import Client
from config import Config
import time
import random

def download_media(url, is_audio=False):
    """
    Debug Version: Returns the error message string if it fails,
    instead of just None.
    """
    instances = [
        "https://api.cobalt.tools/api/json",      
        "https://cobalt.xy24.eu/api/json",       
        "https://cobalt.arms.nu/api/json"
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
    if is_audio: payload.update({"isAudioOnly": "true", "aFormat": "mp3"})

    last_error = ""

    # 1. Try Cobalt
    for base_url in instances:
        try:
            # print(f"Trying: {base_url}")
            resp = requests.post(base_url, json=payload, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                last_error = f"{base_url} returned {resp.status_code}"
                continue
                
            data = resp.json()
            if "url" in data: return data["url"]
            if "picker" in data: return data["picker"][0]["url"]
            if "audio" in data: return data["audio"]
            
        except Exception as e:
            last_error = f"{base_url} Error: {str(e)}"
            continue

    # 2. Try Fallback
    try:
        if not is_audio: 
            api_url = f"https://www.dlpanda.com/api/downloader/video?url={url}"
            resp = requests.get(api_url, timeout=15).json()
            if resp and 'url' in resp:
                 return resp['url']
    except Exception as e:
        last_error += f" | Backup Error: {e}"

    # Return the logs so we can show them in chat
    return f"All Servers Failed.\nLast Error: {last_error}"

async def run_lookup(number):
    if not Config.SESSION_STRING: return "⚠️ Config Error: SESSION_STRING missing"
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    try:
        async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            for bot in bots:
                try:
                    sent = await app.send_message(bot, number)
                    await asyncio.sleep(5) 
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id:
                            return f"🕵️ Info ({bot}):\n{msg.text}"
                except Exception as e:
                    return f"⚠️ Bot {bot} Error: {e}"
    except Exception as e:
        return f"❌ Pyrogram Error: {e}"

    return "❌ No Response from Telegram Bots"

def truecaller_lookup(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except Exception as e: 
        return f"❌ System Error: {e}"
