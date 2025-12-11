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
    return "Ping Pong! Bot is Auto-Healing. 🏓"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    print("🤖 Bot Starting...")
    
    # --- 🧠 SMART AI LOADER (Auto-Selects Best Model) ---
    genai.configure(api_key=Config.GEMINI_KEY)
    model = None
    try:
        print("📋 Google se models ki list maang raha hu...")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"📋 Models Found: {available_models}")
        
        # Best Model Priority List
        target_model = ""
        if 'models/gemini-1.5-flash' in available_models:
            target_model = 'gemini-1.5-flash'
        elif 'models/gemini-pro' in available_models:
            target_model = 'gemini-pro'
        elif available_models:
            target_model = available_models[0] # Jo pehla mile wo lelo
            
        if target_model:
            # 'models/' prefix hatana padta hai kabhi kabhi
            clean_name = target_model.replace("models/", "")
            model = genai.GenerativeModel(clean_name)
            print(f"✅ AI Brain Connected to: {clean_name}")
        else:
            print("❌ Koi bhi Model available nahi hai API Key par.")
            
    except Exception as e:
        print(f"⚠️ AI Init Error: {e}")
        model = None
    # ----------------------------------------------------

    cl = Client()

    # --- 🔐 SESSION LOGIN ---
    try:
        print("🔄 Loading Session...")
        session_data = json.loads(Config.INSTA_SESSION)
        cl.set_settings(session_data)
        
        try:
            cl.get_timeline_feed()
            print("✅ Session Valid!")
        except Exception:
            print("⚠️ Session Weak. Password Login trying...")
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
            print("✅ Login Success via Password!")

    except Exception as e:
        print(f"❌ Login Fail: {e}")
        return

    def process():
        try:
            threads = cl.direct_threads(selected_filter="unread")
            
            for t in threads:
                msg = t.messages[0]; text = msg.text; uid = t.users[0].pk
                print(f"📩 Msg from {uid}: {text}")
                
                # A. DOWNLOAD
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("⬇️ Downloading...", [uid])
                    is_music = "spotify" in text and "http" in text
                    link = download_media(text, is_music)
                    if link: cl.direct_send(f"✅ Link:\n{link}", [uid])
                    else: cl.direct_send("❌ Failed.", [uid])
                
                # B. MUSIC
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
                            cl.direct_send(f"⚠️ AI Music Error: {str(e)}", [uid])
                    else:
                        cl.direct_send("❌ AI Connect nahi hua.", [uid])

                # C. TRUECALLER
                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🔍 Checking...", [uid])
                    try: cl.direct_send(truecaller_lookup(text), [uid])
                    except: cl.direct_send("❌ Search Error", [uid])

                # D. CHAT
                else:
                    hist = get_user_memory(uid)
                    if model:
                        try:
                            prompt = f"Hinglish Assistant. History:\n{hist}\nUser: {text}\nReply:"
                            response = model.generate_content(prompt)
                            cl.direct_send(response.text, [uid])
                            save_interaction(uid, text, response.text)
                        except Exception as e:
                            cl.direct_send(f"⚠️ AI Chat Error: {str(e)}", [uid])
                    else:
                        cl.direct_send("AI System Offline (Check Logs).", [uid])

        except Exception as e: print(f"Loop Error: {e}")

    while True: process(); time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
