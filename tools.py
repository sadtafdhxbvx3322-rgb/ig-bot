import requests
import asyncio
from pyrogram import Client
from config import Config

def download_media(url, is_audio=False):
    """Downloads media using the external Cobalt API."""
    try:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        payload = {"url": url, "vQuality": "720", "filenamePattern": "classic"}
        if is_audio: payload.update({"isAudioOnly": "true", "aFormat": "mp3"})
        
        resp = requests.post("https://api.cobalt.tools/api/json", json=payload, headers=headers).json()
        
        if "url" in resp: return resp["url"]
        if "picker" in resp: return resp["picker"][0]["url"]
        
        return None
    except Exception as e: 
        print(f"Cobalt Download Error: {e}")
        return None

async def run_lookup(number):
    """Async Pyrogram function to look up number info via Telegram bots."""
    if not Config.SESSION_STRING: return "⚠️ Telegram Session Missing (Check Env Var)"
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]
    
    async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
        for bot in bots:
            try:
                # 1. Message bhejenge aur uska ID store karenge
                sent = await app.send_message(bot, number)
                
                await asyncio.sleep(8)
                
                # 2. History check karenge, limit 5 tak badha denge
                async for msg in app.get_chat_history(bot, limit=5):
                    
                    # 3. Check: msg.id > sent.id ensures it's a *new* reply to our message.
                    if msg.id > sent.id and len(msg.text) > 20 and "start" not in msg.text.lower():
                        return f"🕵️ **Info ({bot}):**\n{msg.text}"
                        
            except Exception as e:
                print(f"Telegram Bot Error on {bot}: {e}")
                continue
    return "❌ No Data Found or Telegram Bridge Failed"

def truecaller_lookup(n):
    """Synchronous wrapper for truecaller_lookup."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(run_lookup(n))
        loop.close()
        return res
    except Exception as e: 
        return f"Error during Pyrogram Loop Setup: {e}"
