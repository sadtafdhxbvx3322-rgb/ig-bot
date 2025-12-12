import requests
import asyncio
from pyrogram import Client
from config import Config

def download_media(url, is_audio=False):
    """
    Attempts to download media using Cobalt (Primary) and a generic mirror (Secondary).
    """
    # --- 1. Cobalt Attempt (Primary, Stable Backup Instance) ---
    try:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {"url": url, "vQuality": "720", "filenamePattern": "classic"}
        if is_audio: 
            payload.update({"isAudioOnly": "true", "aFormat": "mp3"})
        
        # Using the stable backup instance URL
        resp = requests.post("https://cobalt.api.kwiatekmiki.pl/api/json", json=payload, headers=headers, timeout=15).json()
        
        if "url" in resp: return resp["url"]
        if "picker" in resp: return resp["picker"][0]["url"]
    except Exception as e:
        print(f"⚠️ Cobalt Failed ({e}). Trying Mirror...")

    # --- 2. Generic Mirror Attempt (Secondary Fallback) ---
    try:
        # Note: This generic mirror might not support all media types (like shorts/audios).
        # We use a simple publicly available download mirror
        api_url = f"https://d-downloader.site/api/v2/dl?url={url}" 
        resp = requests.get(api_url, timeout=15).json()
        
        if resp and 'url' in resp:
            # Handle list or direct URL response from the mirror
            if isinstance(resp['url'], list) and resp['url']:
                 return resp['url'][0]['url']
            elif isinstance(resp['url'], str):
                 return resp['url']

    except Exception as e: 
        print(f"❌ Final Download Fail: {e}")
        return None
    
    return None # If both fail

async def run_lookup(number):
    """Async Pyrogram function to look up number info via Telegram bots."""
    if not Config.SESSION_STRING: return "⚠️ Telegram Session Missing (Check Env Var)"
    
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]
    
    # Client initialization 
    async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
        for bot in bots:
            try:
                # 1. Message ID based sending
                sent = await app.send_message(bot, number)
                
                await asyncio.sleep(8) 
                
                # 2. History check (limit 5 to check for newer messages)
                async for msg in app.get_chat_history(bot, limit=5):
                    
                    # 3. Message ID Check: msg.id > sent.id ensures it's a *new* reply to our message.
                    if msg.id > sent.id and len(msg.text) > 20 and "start" not in msg.text.lower():
                        return f"🕵️ **Info ({bot}):**\n{msg.text}"
                        
            except Exception as e:
                print(f"❌ Telegram Bot Error on {bot}: {e}")
                continue
    return "❌ No Data Found or Telegram Bridge Failed"

def truecaller_lookup(n):
    """Synchronous wrapper for truecaller_lookup."""
    try:
        # Runs the async code in the sync Flask/Instagrapi environment
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except Exception as e: 
        return f"❌ Pyrogram Loop Setup Error: {e}"
