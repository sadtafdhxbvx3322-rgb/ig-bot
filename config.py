import os
from dotenv import load_dotenv

# Load .env file (for local testing)
load_dotenv() 

class Config:
    # --- 1. INSTAGRAM ---
    INSTA_USER = os.environ.get("INSTA_USER")
    INSTA_PASS = os.environ.get("INSTA_PASS")
    INSTA_SESSION = os.environ.get("INSTA_SESSION")

    # --- 2. AI & DB ---
    GEMINI_KEY = os.environ.get("GEMINI_KEY")
    MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGO_URL")

    # --- 3. TELEGRAM BRIDGE (Safety Check) ---
    TG_API_ID = 0
    try:
        tg_id_str = os.environ.get("TG_API_ID")
        if tg_id_str:
             TG_API_ID = int(tg_id_str.strip())
    except ValueError:
        print("🚨 Config Error: TG_API_ID must be a number.")

    TG_API_HASH = os.environ.get("TG_API_HASH")
    SESSION_STRING = os.environ.get("SESSION_STRING")

    # --- 4. TARGET BOTS ---
    PRIMARY_BOT = os.environ.get("PRIMARY_BOT", "CYBERINFOXXXBOT")
    BACKUP_BOT = os.environ.get("BACKUP_BOT", "TrueCalleRobot")
