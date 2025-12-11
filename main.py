import os, time, threading
from flask import Flask
from instagrapi import Client
import google.generativeai as genai
from tools import download_media, truecaller_lookup
from database import get_user_memory, save_interaction
from config import Config

app = Flask(__name__)
@app.route('/')
def home(): return "Tau Bot Live! 🚀"
def run_web(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

def run_bot():
    print("🤖 Starting...")
    genai.configure(api_key=Config.GEMINI_KEY)
    model = genai.GenerativeModel('gemini-pro')
    cl = Client()
    try: cl.login(Config.INSTA_USER, Config.INSTA_PASS)
    except Exception as e: print(f"Login Failed: {e}"); return

    def process():
        try:
            for t in cl.direct_threads(selected_filter="unread"):
                msg = t.messages[0]; text = msg.text; uid = t.users[0].pk
                print(f"📩 {uid}: {text}")
                
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("⬇️ Downloading...", [uid])
                    is_music = "spotify" in text and "http" in text
                    link = download_media(text, is_music)
                    cl.direct_send(f"✅ Link:\n{link}" if link else "❌ Failed", [uid])
                
                elif text.lower().startswith(("play ", "bajao ")):
                    song = text[5:]
                    cl.direct_send(f"🔎 Searching {song}...", [uid])
                    ai_url = model.generate_content(f"YouTube Music URL for '{song}'. Only URL.").text.strip()
                    link = download_media(ai_url, True) if "http" in ai_url else None
                    cl.direct_send(f"🎶 Audio:\n{link}" if link else "❌ Not found", [uid])

                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🔍 Checking CyberInfo...", [uid])
                    cl.direct_send(truecaller_lookup(text), [uid])

                else:
                    hist = get_user_memory(uid)
                    reply = model.generate_content(f"Hinglish AI. History:\n{hist}\nUser: {text}").text
                    cl.direct_send(reply, [uid])
                    save_interaction(uid, text, reply)
                
                cl.direct_thread_mark_seen(t.id)
        except Exception as e: print(f"Error: {e}")

    while True: process(); time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    run_bot()
