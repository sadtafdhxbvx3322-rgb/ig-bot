# tools.py ke andar run_lookup function ko isse replace kar do:

async def run_lookup(number):
    if not Config.SESSION_STRING: return "⚠️ Session Missing"
    bots = [Config.PRIMARY_BOT, Config.BACKUP_BOT]
    
    # Client ko loop se pehle shuru karo
    async with Client("worker", api_id=Config.TG_API_ID, api_hash=Config.TG_API_HASH, session_string=Config.SESSION_STRING, in_memory=True) as app:
        for bot in bots:
            try:
                # 1. Message bhejenge aur uska ID store karenge
                sent = await app.send_message(bot, number)
                
                # Bot ko reply karne ka time denge
                await asyncio.sleep(8)
                
                # 2. History check karenge, limit 5 tak badha denge
                async for msg in app.get_chat_history(bot, limit=5):
                    
                    # 3. Yahan check ho raha hai: Kya yeh reply mere bheje hue message (sent.id) se NAYA hai?
                    # Aur kya yeh bot ka reply kisi command ya empty text se bada hai?
                    if msg.id > sent.id and len(msg.text) > 20 and "start" not in msg.text.lower():
                        return f"🕵️ **Info ({bot}):**\n{msg.text}"
                        
            except Exception as e:
                # Agar koi bot down ho, toh agle bot pe chala jayega
                print(f"Telegram Bot Error on {bot}: {e}")
                continue
    return "❌ No Data Found"
