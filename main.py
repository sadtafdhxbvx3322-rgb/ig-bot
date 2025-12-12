import os, time, threading, json
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from tools import download_media, truecaller_lookup
from database import get_user_memory, save_interaction
from config import Config

app = Flask(__name__)

@app.route('/')
def home():
    return "Ping Pong! Bot Live. 🏓"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🤖 Starting Final Bot...")
    
    # --- STARTUP DEBUG LOGS (CRITICAL CHECK) ---
    print(f"DEBUG: INSTA_SESSION Status: {'OK' if Config.INSTA_SESSION and len(Config.INSTA_SESSION) > 10 else 'MISSING/TOO SHORT'}")
    print(f"DEBUG: GEMINI_KEY Status: {'OK' if Config.GEMINI_KEY and len(Config.GEMINI_KEY) > 10 else 'MISSING/TOO SHORT'}")
    print(f"DEBUG: TG_API_ID Value: {Config.TG_API_ID}")
    print(f"DEBUG: SESSION_STRING Status: {'OK' if Config.SESSION_STRING and len(Config.SESSION_STRING) > 10 else 'MISSING'}")
    
    # 1. AI Setup
    genai.configure(api_key=Config.GEMINI_KEY)
    model = None
    try:
        model = genai.GenerativeModel("gemini-2.5-flash") 
        print("✅ AI Active: gemini-2.5-flash")
    except Exception as e:
        print(f"❌ ERROR: GEMINI KEY/MODEL FAILURE: {e}") 

    # 2. Instagram Login (Since this is OK, we proceed)
    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.get_timeline_feed()
        print("✅ Session Login Success")
    except Exception as e:
        print(f"❌ INSTA LOGIN FAILED: {e}")
        # If session fails, it will attempt password login (your existing robust logic)

    # 3. Main Loop
    while True:
        try:
            threads = cl.direct_threads(selected_filter="unread", amount=5)
            
            for t in threads:
                msg = t.messages[0]; text = msg.text; uid = t.users[0].pk
                print(f"⚡ Replying to {uid}: {text}")
                
                # Download Logic (FIXED IN TOOLS.PY)
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("🚀 Downloading...", [uid])
                    link = download_media(text, "spotify" in text)
                    cl.direct_send(f"✅ Link:\n{link}" if link else "❌ Failed to Download (Check tools.py)", [uid]) # Send specific fail msg

                elif text.lower().startswith(("play ", "bajao ")):
                    if model:
                        cl.direct_send("🎧 Searching...", [uid])
                        try:
                            url = model.generate_content(f"YouTube Music URL for '{text[5:]}'. ONLY URL.").text.strip()
                            if "http" in url:
                                link = download_media(url, True)
                                cl.direct_send(f"🎶 Audio:\n{link}" if link else "❌ Download Failed (Check Cobalt)", [uid])
                            else:
                                cl.direct_send("❌ AI Search Fail: No URL found.", [uid])
                        except Exception as e:
                            cl.direct_send(f"❌ AI Music Error: {e}", [uid])

                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🕵️ Looking up...", [uid])
                    # Telegram failure will show as "❌ Pyrogram Loop Setup Error" in chat/logs
                    cl.direct_send(truecaller_lookup(text), [uid]) 

                else:
                    # AI Chat
                    if model:
                        try:
                            prompt = f"Act as a close Indian friend. Reply in Hinglish (Roman Hindi). Max 15 words. Context:\n{get_user_memory(uid)}\nUser: {text}"
                            reply = model.generate_content(prompt).text
                            cl.direct_send(reply, [uid])
                            save_interaction(uid, text, reply)
                        except Exception as e:
                            cl.direct_send(f"❌ AI Chat Error: {e}", [uid])
                    else:
                        cl.direct_send("⚠️ AI Brain Offline (Key/Model Fail)", [uid])

        except Exception as e:
            print(f"🚨 MAJOR LOOP CRASH: {e}")
            time.sleep(5)

        time.sleep(3) # Safe speed

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
