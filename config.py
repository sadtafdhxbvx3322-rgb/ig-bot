import os

class Config:
    # 1. INSTAGRAM
    INSTA_USER = os.environ.get("INSTA_USER")
    INSTA_PASS = os.environ.get("INSTA_PASS")
    # The JSON session will be loaded from the secure vault
    INSTA_SESSION = os.environ.get("INSTA_SESSION")

    # 2. AI & DB
    GEMINI_KEY = os.environ.get("GEMINI_KEY")
    MONGO_URI = os.environ.get("MONGO_URI")

    # 3. TELEGRAM BRIDGE
    # We use 'int' here because API_ID must be a number
    TG_API_ID = int(os.environ.get("TG_API_ID", "0")) 
    TG_API_HASH = os.environ.get("TG_API_HASH")
    SESSION_STRING = os.environ.get("SESSION_STRING")

    # 4. TARGET BOTS (These are not secret, but good to keep flexible)
    PRIMARY_BOT = os.environ.get("PRIMARY_BOT", "CYBERINFOXXXBOT")
    BACKUP_BOT = os.environ.get("BACKUP_BOT", "TrueCalleRobot")
