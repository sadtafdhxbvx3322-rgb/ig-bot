import pymongo
from config import Config
from datetime import datetime

# Initialize connection safely
try:
    # Attempt to connect
    client = pymongo.MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['InstaSuperBot']
    users_col = db['users']
    
    # Test the connection to ensure it's real
    client.server_info()
    print("✅ MongoDB Connection Established")
except Exception as e: 
    users_col = None
    print(f"⚠️ MongoDB Failed (Bot will run without memory): {e}")

def get_user_memory(user_id):
    # FIX: Explicit check for None
    if users_col is None: 
        return ""
    
    try:
        data = users_col.find_one({"_id": user_id})
        if not data or "history" not in data: return ""
        # Return last 5 interactions
        return "\n".join([f"User: {h['u']}\nBot: {h['b']}" for h in data['history'][-5:]])
    except: return ""

def save_interaction(uid, u_msg, b_msg):
    # FIX: Explicit check for None
    if users_col is not None:
        try:
            users_col.update_one(
                {"_id": uid}, 
                {"$push": {"history": {"u": u_msg, "b": b_msg}}, "$setOnInsert": {"joined": datetime.now()}}, 
                upsert=True
            )
        except Exception as e:
            print(f"⚠️ DB Save Error: {e}")
