import requests
import asyncio
from pyrogram import Client
from config import Config

# --- 1. DOWNLOADER ENGINE (Cobalt) ---
def download_media(url, is_audio=False):
    try:
        payload = {"url": url, "vQuality": "720", "filenamePattern": "classic"}
        if is_audio: payload.update({"isAudioOnly": "true", "aFormat": "mp3"})
        
        resp = requests.post("https://api.cobalt.tools/api/json", json=payload, headers={"Accept": "application/json", "Content-Type": "application/json"}).json()
        
        if "url" in resp: return resp["url"]
        if "picker" in resp: return resp["picker"][0]["url"]
        return None
    except: return None

# --- 2. TELEGRAM LOOKUP ENGINE (Smart Switcher) ---
async def get_telegram_lookup(number):
    if not Config.SESSION_STRING: return "⚠️ Session String Missing"
    
    # Bots ki list: Pehle Primary try karenge, fir Backup
    bots_to_try = [Config.PRIMARY_BOT, Config.BACKUP_BOT]

    async with Client("bot_worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING) as app:
        
        for bot_username in bots_to_try:
            try:
                print(f"🔄 Trying {bot_username} for {number}...")
                sent = await app.send_message(bot_username, number)
                
                # 8 Second wait for reply
                await asyncio.sleep(8)
                
                # Check reply
                async for message in app.get_chat_history(bot_username, limit=1):
                    if message.id > sent.id:
                        # Agar reply mein 'Start' ya error nahi hai toh return karo
                        if "start" not in message.text.lower():
                            return f"🕵️ **Report by {bot_username}:**\n{message.text}"
                
                print(f"❌ {bot_username} did not reply. Switching...")
            except Exception as e:
                print(f"⚠️ Error with {bot_username}: {e}")
                continue # Try next bot

        return "❌ Dono Bots ne jawab nahi diya. Baad mein try karna."

def truecaller_lookup(n):
    try: return asyncio.run(get_telegram_lookup(n))
    except: return "System Error"
