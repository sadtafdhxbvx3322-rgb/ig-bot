import requests
import asyncio
from pyrogram import Client
from config import Config

def download_media(url, is_audio=False):
    try:
        payload = {"url": url, "vQuality": "720", "filenamePattern": "classic"}
        if is_audio: payload.update({"isAudioOnly": "true", "aFormat": "mp3"})
        resp = requests.post("https://api.cobalt.tools/api/json", json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"}).json()
        if "url" in resp: return resp["url"]
        if "picker" in resp: return resp["picker"][0]["url"]
        return None
    except: return None

async def get_telegram_lookup(number):
    if not Config.SESSION_STRING or "PASTE" in Config.SESSION_STRING: return "⚠️ Session String Missing"
    
    # Bots List from Config
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    async with Client("bot_worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING) as app:
        for bot in bots:
            try:
                print(f"🔄 Trying {bot}...")
                sent = await app.send_message(bot, number)
                await asyncio.sleep(8)
                async for msg in app.get_chat_history(bot, limit=1):
                    if msg.id > sent.id and "start" not in msg.text.lower():
                        return f"🕵️ **Report ({bot}):**\n{msg.text}"
            except: continue
        return "❌ All bots busy/failed."

def truecaller_lookup(n):
    try: return asyncio.run(get_telegram_lookup(n))
    except: return "System Error"
