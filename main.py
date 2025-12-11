import os
import time
import threading
import json
import asyncio
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from tools import download_media, truecaller_lookup
from database import get_user_memory, save_interaction
from config import Config

app = Flask(__name__)

@app.route('/')
def home():
    return "Ping Pong! Bot is Live & Debugging. 🏓"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    print("🤖 Bot Starting...")
    
    # --- 1. AI SETUP (Gemini 1.5 Flash) ---
    genai.configure(api_key=Config.GEMINI_KEY)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ AI Brain Connected")
    except Exception as e:
        print(f"⚠️ AI Init Error: {e}")
        model = None

    cl = Client()

    # --- 2. LOGIN LOGIC ---
    try:
        print("🔄 Loading Session...")
        session_data = json.loads(Config.INSTA_SESSION)
        cl.set_settings(session_data)
        
        try:
            cl.get_timeline_feed()
            print("✅ Session Valid!")
        except Exception:
            print("⚠️ Session Weak. Trying Password...")
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
            print("✅ Login Success via Password!")

    except Exception as e:
        print(f"❌ Login Fail: {e}")
        return

    def process():
        try:
            threads = cl.direct_threads(selected_filter="unread")
            
            for t in threads:
                msg = t.messages[0]
                text = msg.text
                uid = t.users[0].pk
                print(f"📩 Msg from {uid}: {text}")
                
                # --- A. DOWNLOAD ---
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("⬇️ Downloading...", [uid])
                    is_music = "spotify" in text and "http" in text
                    link = download_media(text, is_music)
                    if link: cl.direct_send(f"✅ Link:\n{link}", [uid])
                    else: cl.direct_send("❌ Failed.", [uid])
                
                # --- B. MUSIC ---
                elif text.lower().startswith(("play ", "bajao ")):
                    song = text[5:]
                    cl.direct_send(f"🔎 Searching {song}...", [uid])
                    if model:
                        try:
                            ai_url = model.generate_content(f"YouTube Music URL for '{song}'. Output ONLY URL.").text.strip()
                            if "http" in ai_url:
                                link = download_media(ai_url, True)
                                if link: cl.direct_send(f"🎶 Audio:\n{link}", [uid])
                                else: cl.direct_send("❌ Audio Error.", [uid])
                            else: cl.direct_send("❌ Song nahi mila.", [uid])
                        except Exception as e:
                            # ERROR DIKHAO CHAT MEIN
                            cl.direct_send(f"⚠️ Music AI Error: {str(e)}", [uid])
                    else:
                        cl.direct_send("❌ AI Offline.", [uid])

                # --- C. NUMBER ---
                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🔍 Checking...", [uid])
                    try:
                        info = truecaller_lookup(text)
                        cl.direct_send(info, [uid])
                    except: cl.direct_send("❌ Search Error", [uid])

                # --- D. CHAT ---
                else:
                    hist = get_user_memory(uid)
                    if model:
                        try:
                            prompt = f"You are a friendly Hinglish AI assistant on Instagram. Short reply.\nHistory:\n{hist}\nUser: {text}"
                            response = model.generate_content(prompt)
                            reply = response.text
                        except Exception as e:
                            # YAHAN HAI ASLI JUGAD: Error user ko bhej do
                            reply = f"⚠️ AI Error: {str(e)}"
                            print(f"AI Gen Error: {e}")
                    else:
                        reply = "AI System Offline."
                        
                    cl.direct_send(reply, [uid])
                    save_interaction(uid, text, reply)

        except Exception as e:
            print(f"Loop Error: {e}")

    while True:
        process()
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
