# main.py ke last mein jo "while True" loop hai, usse isse replace kar:

    while True:
        try:
            # 1. Check Messages (Sirf 5 latest unread)
            threads = cl.direct_threads(selected_filter="unread", amount=5)
            
            for t in threads:
                msg = t.messages[0]
                text = msg.text
                uid = t.users[0].pk
                
                print(f"⚡ Fast Reply to {uid}: {text}")

                # Processing...
                if "instagram.com" in text or "youtu" in text:
                    cl.direct_send("🚀 Downloading...", [uid])
                    link = download_media(text, "spotify" in text)
                    cl.direct_send(f"✅ Link:\n{link}" if link else "❌ Failed", [uid])
                
                elif text.lower().startswith(("play ", "bajao ")):
                    if model:
                        cl.direct_send("🎧 Searching...", [uid])
                        url = model.generate_content(f"YouTube Music URL for '{text[5:]}'. ONLY URL.").text.strip()
                        if "http" in url:
                            link = download_media(url, True)
                            cl.direct_send(f"🎶 Audio:\n{link}" if link else "❌ Error", [uid])
                        else:
                            cl.direct_send("❌ Song Not Found", [uid])

                elif text.startswith("+91") or (text.isdigit() and len(text)>9):
                    cl.direct_send("🕵️ Jasoosi shuru...", [uid])
                    cl.direct_send(truecaller_lookup(text), [uid])
                
                else:
                    # AI Chat
                    if model:
                        # Prompt ko fast aur short rakha hai
                        prompt = f"Act as a close friend. Reply in Hinglish (Roman Hindi). Max 1 sentence. Context:\n{get_user_memory(uid)}\nUser: {text}"
                        reply = model.generate_content(prompt).text
                        cl.direct_send(reply, [uid])
                        save_interaction(uid, text, reply)
                    else:
                        cl.direct_send("⚠️ AI Brain Missing (Check Key)", [uid])

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5) # Error aaye toh thoda rukna padega

        # 🚀 SUPER FAST SPEED (Lekin Ban nahi hoga)
        time.sleep(2) 
