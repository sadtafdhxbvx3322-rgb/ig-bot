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
    print("🤖 Starting Fast Bot...")
    
    # 1. AI Setup
    genai.configure(api_key=Config.GEMINI_KEY)
    model = None
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        print("✅ AI Active")
    except Exception as e:
        print(f"⚠️ AI Error: {e}")

    # 2. Instagram Login
    cl = Client()
    try:
        # Session se login (Fast & Safe)
        cl.set_settings(json.loads(Config.INSTA_SESSION))
        cl.get_timeline_feed()
        print("✅ Session Login Success")
    except Exception as e:
        print(f"⚠️ Session Fail: {e}")
        try:
            # Backup Password Login
            cl.login(Config.INSTA_USER, Config.INSTA_PASS)
            print("✅ Password Login Success")
        except Exception as e2:
            print(f"❌ Login Failed: {e2}")

    # 3. Main Loop (Fast Speed)
    while True:
        try:
            # Sirf 5 latest unread messages uthao
            threads = cl.direct_threads(selected_filter="unread", amount=5)
            
            for t in threads:
                msg = t.messages[0]
                text = msg.text
                uid = t.users[0].pk
                
                print(f"⚡ Fast Reply to {uid}: {text}")
                
                # Logic Start
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("🚀 Downloading...", [uid])
                    link = download_media(text, "spotify" in text)
                    cl.direct_send(f"✅ Link:\n{link}" if link else "❌ Failed", [uid])

                elif text.lower().startswith(("play ", "bajao ")):
                    if model:
                        cl.direct_send("🎧 Searching...", [uid])
                        try:
                            url = model.generate_content(f"YouTube Music URL for '{text[5:]}'. ONLY URL.").text.strip()
                            if "http" in url:
                                link = download_media(url, True)
                                cl.direct_send(f"🎶 Audio:\n{link}" if link else "❌ Error", [uid])
                            else:
                                cl.direct_send("❌ Song Not Found", [uid])
                        except:
                            cl.direct_send("❌ AI Error", [uid])

                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🕵️ Looking up...", [uid])
                    cl.direct_send(truecaller_lookup(text), [uid])

                else:
                    # AI Chat (Short & Human-like)
                    if model:
                        try:
                            # Prompt updated for short, hinglish replies
                            prompt = f"Act as a close Indian friend. Reply in Hinglish (Roman Hindi). Max 15 words. No formal drama. Context:\n{get_user_memory(uid)}\nUser: {text}"
                            reply = model.generate_content(prompt).text
                            cl.direct_send(reply, [uid])
                            save_interaction(uid, text, reply)
                        except:
                            cl.direct_send("AI Error", [uid])
                    else:
                        cl.direct_send("⚠️ AI Brain Offline", [uid])

        except Exception as e:
            print(f"⚠️ Loop Error: {e}")
            time.sleep(5)

        # FAST SPEED (Safe)
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
