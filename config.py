import os
from dotenv import load_dotenv

# Optional: Load .env file if running locally, but Render ignores this.
load_dotenv() 

class Config:
    # --- 1. INSTAGRAM (Read from Render Environment Variables) ---
    INSTA_USER = os.environ.get("INSTA_USER", "glitch.tools")
    INSTA_PASS = os.environ.get("INSTA_PASS")
    INSTA_SESSION = os.environ.get("INSTA_SESSION")

    # --- 2. AI & DB ---
    GEMINI_KEY = os.environ.get("GEMINI_KEY")
    MONGO_URI = os.environ.get("MONGO_URI")

    # --- 3. TELEGRAM BRIDGE (Error-Proofing for Integer Values) ---
    # Python needs TG_API_ID to be an integer (number). We handle errors gracefully.
    TG_API_ID = 0
    try:
        tg_id_str = os.environ.get("TG_API_ID")
        if tg_id_str:
             # This handles the "invalid literal" error by stripping whitespace and converting
             TG_API_ID = int(tg_id_str.strip()) 
    except ValueError:
        print("🚨 CRITICAL ERROR: TG_API_ID in Env Vars must be ONLY numbers. Using 0.")
        
    TG_API_HASH = os.environ.get("TG_API_HASH")
    SESSION_STRING = os.environ.get("SESSION_STRING")

    # --- 4. TARGET BOTS ---
    PRIMARY_BOT = os.environ.get("PRIMARY_BOT", "CYBERINFOXXXBOT")
    BACKUP_BOT = os.environ.get("BACKUP_BOT", "TrueCalleRobot")

