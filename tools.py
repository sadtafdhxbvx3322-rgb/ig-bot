import requests
import asyncio
from pyrogram import Client
from config import Config
import time
import random

def download_media(url, is_audio=False):
    """
    Robust media downloader. Rotates through multiple Cobalt mirrors 
    to find one that works.
    """
    # FRESH LIST OF WORKING MIRRORS (2025)
    instances = [
        "https://api.cobalt.tools/api/json",      # Official
        "https://cobalt.xy24.eu/api/json",        # Mirror 1
        "https://api.server.cobalt.tools/api/json", # Mirror 2
        "https://cobalt.arms.nu/api/json",        # Mirror 3
        "https://cobalt.royale.us.kg/api/json"    # Mirror 4
    ]
    random.shuffle(instances) # Shuffle to avoid rate limits

    # FAKE BROWSER HEADERS (Crucial to bypass blocks)
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

    # --- 1. Try Cobalt Mirrors ---
    for base_url in instances:
        try:
            print(f"🔄 Trying download via: {base_url}...")
            resp = requests.post(base_url, json=payload, headers=headers, timeout=10)
            
            if resp.status_code == 429: # Rate limited
                continue
                
            data = resp.json()
            
            # Check for success keys
            if "url" in data: return data["url"]
            if "picker" in data: return data["picker"][0]["url"]
            if "audio" in data: return data["audio"]
            
        except Exception as e:
            print(f"⚠️ Mirror failed: {e}")
            continue

    # --- 2. Emergency Fallback (DLPanda) ---
    print("⚠️ All Cobalt mirrors failed. Trying Emergency Backup...")
    try:
        if not is_audio: 
            api_url = f"https://www.dlpanda.com/api/downloader/video?url={url}"
            resp = requests.get(api_url, timeout=15).json()
            if resp and 'url' in resp:
                 return resp['url']
    except: pass

    return None

async def run_lookup(number):
    """Async Pyrogram lookup."""
    if not Config.SESSION_STRING: return "⚠️ Telegram Config Missing"
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    try:
        async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
            for bot in bots:
                try:
                    sent = await app.send_message(bot, number)
                    await asyncio.sleep(5) 
                    async for msg in app.get_chat_history(bot, limit=3):
                        if msg.id > sent.id:
                            return f"🕵️ **Info:**\n{msg.text}"
                except: continue
    except Exception as e:
        return f"❌ TG Error: {e}"

    return "❌ No Data Found."

def truecaller_lookup(n):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except Exception as e: 
        return f"❌ System Error: {e}"
