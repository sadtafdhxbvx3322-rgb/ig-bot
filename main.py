import os
import time
import threading
import json
import re
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from tools import download_media, truecaller_lookup
from database import get_user_memory, save_interaction
from config import Config

app = Flask(__name__)
@app.route('/')
def home(): return "Ping Pong! Bot is Live (Gemini Pro). 🏓"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🤖 Bot Starting with GEMINI PRO...")
    
    # --- AI SETUP (Back to Stable Model) ---
    try:
        genai.configure(api_key=Config.GEMINI_KEY)
        # 👇 Yahan wapas 'gemini-pro' kar diya hai taaki 404 Error na aaye
        model = genai.GenerativeModel('gemini-pro')
    except Exception as e:
        print(f"❌ AI Setup Error: {e}")

    cl = Client()

    # --- LOGIN LOGIC ---
    try:
        print("🔄 Loading Session...")
        session_data = json.loads(Config.INSTA_SESSION)
        cl.set_settings(session_data)
        
        try:
            cl.get_timeline_feed()
            print("✅ Session Valid! Bot Online.")
        except:
            print("⚠️ Session Expired? Password Login Trying...")
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
            print("✅ Login Success via Password!")

    except Exception as e:
        print(f"❌ Critical Login Fail: {e}")
        return

    def process():
        try:
            threads = cl.direct_threads(selected_filter="unread")
            for t in threads:
                msg = t.messages[0]; text = msg.text; uid = t.users[0].pk
                print(f"📩 Msg from {uid}: {text}")
                
                # 1. DOWNLOAD LINKS
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("⬇️ Downloading...", [uid])
                    is_music = "spotify" in text and "http" in text
                    link = download_media(text, is_music)
                    if link:
                        cl.direct_send(f"✅ Ye lo:\n{link}", [uid])
                    else:
                        cl.direct_send("❌ Download Fail.", [uid])
                
                # 2. MUSIC SEARCH
                elif text.lower().startswith(("play ", "bajao ")):
                    song = text[5:]
                    cl.direct_send(f"🔎 Searching '{song}'...", [uid])
                    
                    try:
                        ai_resp = model.generate_content(f"Give me one YouTube Music URL for '{song}'. Only URL nothing else.").text
                        url_match = re.search(r'(https?://\S+)', ai_resp)
                        if url_match:
                            clean_url = url_match.group(0)
                            link = download_media(clean_url, True)
                            if link:
                                cl.direct_send(f"🎶 Ye lo Audio:\n{link}", [uid])
                            else:
                                cl.direct_send("❌ Audio convert nahi hua.", [uid])
                        else:
                            cl.direct_send("❌ Link nahi mila.", [uid])
                    except Exception as e:
                        cl.direct_send(f"⚠️ AI Error: {str(e)}", [uid])

                # 3. TRUECALLER
                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🔍 Checking Info...", [uid])
                    cl.direct_send(truecaller_lookup(text), [uid])

                # 4. AI CHAT
                else:
                    try:
                        hist = get_user_memory(uid)
                        prompt = f"You are a friendly Hinglish AI assistant on Instagram named GlitchBot.\nHISTORY:\n{hist}\nUSER: {text}\nREPLY (Short):"
                        reply = model.generate_content(prompt).text
                        cl.direct_send(reply, [uid])
                        save_interaction(uid, text, reply)
                    except Exception as e:
                        print(f"AI Chat Error: {e}")
                        # Error user ko bhi batao taaki pata chale
                        cl.direct_send("⚠️ Brain Freeze! (AI Error)", [uid])
                
                cl.direct_thread_mark_seen(t.id)
                
        except Exception as e:
            print(f"Loop Error: {e}")

    # Fast Speed (2 Seconds)
    while True: process(); time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
