import os
import time
import threading
import json
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from tools import download_media, truecaller_lookup
from database import get_user_memory, save_interaction
from config import Config

app = Flask(__name__)
@app.route('/')
def home(): return "Ping Pong! Bot is Working via Session. 🏓"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🤖 Bot Starting...")
    genai.configure(api_key=Config.GEMINI_KEY)
    model = genai.GenerativeModel('gemini-pro')
    cl = Client()

    # --- 🔐 NEW LOGIN LOGIC (SESSION JSON) ---
    try:
        print("🔄 Loading Session...")
        
        # String ko wapas JSON (Object) mein convert kar rahe hain
        session_data = json.loads(Config.INSTA_SESSION)
        
        # Instagrapi ko settings de rahe hain
        cl.set_settings(session_data)
        
        # Login verify (Password use karega but Session hone ki wajah se block nahi hoga)
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        print("✅ Login Success via Saved Session!")

    except Exception as e:
        print(f"❌ Login Failed: {e}")
        print("⚠️ Check if Session JSON is pasted correctly in config.py")
        return
    # ----------------------------------------

    def process():
        try:
            for t in cl.direct_threads(selected_filter="unread"):
                msg = t.messages[0]; text = msg.text; uid = t.users[0].pk
                print(f"📩 {uid}: {text}")
                
                # 1. DOWNLOAD LINKS
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("⬇️ Downloading...", [uid])
                    is_music = "spotify" in text and "http" in text
                    link = download_media(text, is_music)
                    cl.direct_send(f"✅ Link:\n{link}" if link else "❌ Failed", [uid])
                
                # 2. MUSIC SEARCH
                elif text.lower().startswith(("play ", "bajao ")):
                    song = text[5:]
                    cl.direct_send(f"🔎 Searching {song}...", [uid])
                    ai_url = model.generate_content(f"YouTube Music URL for '{song}'. Only URL.").text.strip()
                    link = download_media(ai_url, True) if "http" in ai_url else None
                    cl.direct_send(f"🎶 Audio:\n{link}" if link else "❌ Not found", [uid])

                # 3. TRUECALLER / NUMBER
                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🔍 Checking Info...", [uid])
                    cl.direct_send(truecaller_lookup(text), [uid])

                # 4. AI CHAT
                else:
                    hist = get_user_memory(uid)
                    reply = model.generate_content(f"Hinglish AI. History:\n{hist}\nUser: {text}").text
                    cl.direct_send(reply, [uid])
                    save_interaction(uid, text, reply)
                
                cl.direct_thread_mark_seen(t.id)
        except Exception as e: print(f"Loop Error: {e}")

    while True: process(); time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
