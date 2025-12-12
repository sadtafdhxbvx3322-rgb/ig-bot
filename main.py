import os
import time
import threading
import json
import logging
import re  # Added for strict number detection
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
# Import the new local downloader
from tools import download_media, truecaller_lookup, download_file_locally
from config import Config

logging.basicConfig(level=logging.INFO)
for lib in ['urllib3', 'instagrapi', 'httpx', 'httpcore']:
    logging.getLogger(lib).setLevel(logging.WARNING)

app = Flask(__name__)

@app.route('/')
def home(): return "Bot Online"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def get_ai_model():
    try:
        valid = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return genai.GenerativeModel(next((m for m in valid if 'flash' in m), valid[0]))
    except: return None

def ask_ai(model, prompt):
    if not model: return None
    for i in range(3):
        try: return model.generate_content(prompt).text.strip()
        except: time.sleep(2)
    return None

def run_bot():
    print("🚀 Starting Bot...")
    genai.configure(api_key=Config.GEMINI_KEY)
    model = get_ai_model()

    cl = Client()
    try:
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.login(Config.INSTA_USER, Config.INSTA_PASS)
        my_id = str(cl.user_id)
        print(f"✅ Logged in: {my_id}")
    except: return

    print("⚡ Waiting for commands...")
    processed = set()

    while True:
        try:
            threads = cl.direct_threads(amount=3)
            for t in threads:
                if not t.messages: continue
                msg = t.messages[0]
                if msg.id in processed or str(msg.user_id) == my_id: continue
                processed.add(msg.id)

                text = getattr(msg, 'text', "").strip()
                if not text: continue
                
                print(f"📩 Msg: {text}")
                tid = t.pk

                # --- 1. STRICT NUMBER SEARCH (Regex) ---
                # Looks for any sequence of 10+ digits
                number_match = re.search(r'(\+?\d{10,})', text)
                
                if number_match:
                    phone_num = number_match.group(1)
                    cl.direct_answer(tid, f"🕵️ Checking {phone_num}...")
                    res = truecaller_lookup(phone_num)
                    cl.direct_answer(tid, res)
                
                # --- 2. DOWNLOAD & VOICE NOTE ---
                elif "play " in text.lower() or "spotify" in text.lower() or "instagram.com" in text.lower():
                    cl.direct_answer(tid, "🔍 Searching & Downloading...")
                    
                    target = text
                    # Use AI to extract URL if it's a song request
                    if "play " in text.lower() and "http" not in text and model:
                        ai_resp = ask_ai(model, f"Find YouTube URL for '{text}'. Reply ONLY with URL.")
                        if ai_resp and "http" in ai_resp: target = ai_resp.split()[-1]

                    # Get Download Link
                    link = download_media(target, is_audio=True) # Always try Audio for "Play"

                    if link:
                        # Try to send as Voice Note
                        try:
                            # 1. Download to server
                            local_path = download_file_locally(link, "song.mp3")
                            if local_path:
                                # 2. Upload to Insta
                                cl.direct_send_voice(local_path, [t.users[0].pk])
                                # 3. Cleanup
                                os.remove(local_path)
                                cl.direct_answer(tid, "✅ Sent as Voice Note.")
                            else:
                                # Fallback to Link
                                cl.direct_answer(tid, f"✅ Could not upload audio. Here is the link:\n{link}")
                        except Exception as e:
                            print(f"Upload Fail: {e}")
                            cl.direct_answer(tid, f"✅ Link:\n{link}")
                    else:
                        cl.direct_answer(tid, "❌ Could not find song.")

                # --- 3. AI CHAT ---
                elif model:
                    reply = ask_ai(model, f"Reply in Hinglish. User: {text}")
                    if reply: cl.direct_answer(tid, reply)

        except Exception as e:
            print(f"🔥 Error: {e}")
            time.sleep(5)
        
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
