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
    print("🤖 Starting Final Robust Bot...")
    
    # --- STARTUP DEBUG LOGS (CRITICAL CHECK) ---
    print(f"DEBUG: GEMINI_KEY Status: {'OK' if Config.GEMINI_KEY and len(Config.GEMINI_KEY) > 10 else 'MISSING/TOO SHORT'}")
    print(f"DEBUG: TG_API_ID Value: {Config.TG_API_ID}")
    
    # 1. AI Setup
    genai.configure(api_key=Config.GEMINI_KEY)
    model = None
    try:
        model = genai.GenerativeModel("gemini-2.5-flash") 
        print("✅ AI Active: gemini-2.5-flash")
    except Exception as e:
        print(f"❌ ERROR: GEMINI KEY/MODEL FAILURE: {e}") 

    # 2. Instagram Login (Assuming Session is OK)
    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.get_timeline_feed()
        print("✅ Session Login Success")
    except Exception as e:
        print(f"❌ INSTA LOGIN FAILED: {e}")
        # Add password backup login logic here if needed, but session is preferred

    # 3. Main Loop
    while True:
        try:
            threads = cl.direct_threads(selected_filter="unread", amount=5)
            
            for t in threads:
                msg = t.messages[0]; text = msg.text; uid = t.users[0].pk
                print(f"⚡ Replying to {uid}: {text}")
                
                # --- DOWNLOAD & MUSIC LOGIC (FIXED) ---
                is_media_request = "instagram.com" in text or "youtu" in text
                is_audio_request = "spotify" in text or text.lower().startswith(("play ", "bajao "))
                
                if is_media_request or is_audio_request:
                    cl.direct_send("🚀 Downloading...", [uid])
                    
                    url_to_download = text # Default to direct link
                    is_audio = False

                    if is_audio_request and model:
                         is_audio = True
                         # AI finds the URL
                         url_to_download = model.generate_content(f"YouTube Music URL for '{text[5:]}'. ONLY URL.").text.strip()
                         if "http" not in url_to_download:
                             cl.direct_send("❌ AI Search Fail: No valid URL found.", [uid])
                             continue 
                             
                    # Execute Download (tools.py will handle Dual-Download fallback)
                    link = download_media(url_to_download, is_audio)
                    
                    # Send specific fail message based on function
                    cl.direct_send(f"✅ Link:\n{link}" if link else "❌ Failed: External Download API Blocked.", [uid]) 

                # --- TELEGRAM LOGIC (RETRY & CONCURRENCY FIXED) ---
                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🕵️ Looking up...", [uid])
                    
                    # First Attempt
                    result = truecaller_lookup(text)
                    
                    # If Pyrogram setup fails or thread locks, retry once (Fixes intermittent dead issue)
                    if "Pyrogram Loop Setup Error" in result or "No Data Found" in result:
                        print("⚠️ Pyrogram failed on first attempt. Retrying...")
                        time.sleep(5) 
                        result = truecaller_lookup(text) # Second attempt
                    
                    cl.direct_send(result, [uid]) 

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

