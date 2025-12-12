import os
import time
import threading
import json
import logging
import re
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
# Import our fixed tools
from tools import download_media, truecaller_lookup, download_file_locally
from config import Config

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/')
def home(): return "Full Feature Bot Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

# --- AI HELPER ---
def get_ai_reply(model, text):
    try:
        return model.generate_content(f"Reply in Hinglish slang. User: {text}").text.strip()
    except: return None

def get_yt_link(model, text):
    try:
        return model.generate_content(f"Find YouTube URL for '{text}'. Reply ONLY with URL.").text.strip()
    except: return None

def run_bot():
    print("🚀 Starting FULL FEATURE Bot...")

    # 1. AI SETUP
    genai.configure(api_key=Config.GEMINI_KEY)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
    except:
        model = genai.GenerativeModel("gemini-pro")

    # 2. INSTAGRAM LOGIN (The Method that worked)
    cl = Client()
    try:
        try:
            cl.set_settings(json.loads(Config.INSTA_SESSION))
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        except:
            print("⚠️ Session invalid. Logging in with Password...")
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        
        my_id = str(cl.user_id)
        print(f"✅ Login Success. ID: {my_id}")
    except Exception as e:
        print(f"🔥 LOGIN FAILED: {e}")
        return

    # 3. MAIN LOOP
    print("👀 Waiting for commands...")
    processed = set()

    while True:
        try:
            threads = cl.direct_threads(amount=5)

            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                
                # Check Duplicates
                if msg.id in processed: continue
                if str(msg.user_id) == my_id: continue

                processed.add(msg.id)
                text = getattr(msg, 'text', "").strip()
                if not text: continue
                
                print(f"📩 Msg: {text}")
                tid = t.pk

                # ================= FEATURES =================

                # --- A. NUMBER LOOKUP ---
                # Checks for 10+ digits
                number_match = re.search(r'(\+?\d{10,})', text)
                
                if number_match:
                    try:
                        phone = number_match.group(1)
                        cl.direct_answer(tid, f"🕵️ Checking {phone}...")
                        result = truecaller_lookup(phone)
                        cl.direct_answer(tid, result)
                    except Exception as e:
                        cl.direct_answer(tid, f"⚠️ Lookup Failed: {e}")
                
                # --- B. MUSIC / DOWNLOAD ---
                elif "play " in text.lower() or "spotify" in text.lower() or "instagram.com" in text.lower():
                    try:
                        cl.direct_answer(tid, "🔍 Searching...")
                        
                        target_url = text
                        # Use AI to find link if user just said "Play Song Name"
                        if "play " in text.lower() and "http" not in text:
                            ai_link = get_yt_link(model, text)
                            if ai_link and "http" in ai_link:
                                target_url = ai_link.split()[-1]
                        
                        # Get Direct Link
                        direct_url, err = download_media(target_url, is_audio=True)
                        
                        if not direct_url:
                            cl.direct_answer(tid, f"❌ Link Error: {err}")
                        else:
                            # Download Locally & Send
                            path, save_err = download_file_locally(direct_url, "song.m4a")
                            
                            if path:
                                try:
                                    cl.direct_send_voice(path, [t.users[0].pk])
                                    cl.direct_answer(tid, "✅ Sent Voice Note.")
                                    os.remove(path)
                                except Exception as upload_e:
                                    cl.direct_answer(tid, f"❌ Upload Error: {upload_e}\nLink: {direct_url}")
                            else:
                                cl.direct_answer(tid, f"❌ Save Error: {save_err}")

                    except Exception as e:
                        cl.direct_answer(tid, f"⚠️ Music Logic Crash: {e}")

                # --- C. AI CHAT (Default) ---
                else:
                    try:
                        reply = get_ai_reply(model, text)
                        if reply:
                            cl.direct_answer(tid, reply)
                    except Exception as e:
                        cl.direct_answer(tid, f"⚠️ AI Error: {e}")

        except Exception as e:
            print(f"🔥 Loop Error: {e}")
            time.sleep(5)
        
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
