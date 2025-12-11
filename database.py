import pymongo
from config import Config
from datetime import datetime

# Database Connection
try:
    client = pymongo.MongoClient(Config.MONGO_URI)
    db = client['InstaSuperBot']
    users_col = db['users']
except:
    users_col = None

def get_user_memory(user_id):
    if users_col is None: return ""
    try:
        data = users_col.find_one({"_id": user_id})
        if not data or "history" not in data: return ""
        return "\n".join([f"User: {h['user']}\nBot: {h['bot']}" for h in data['history'][-5:]])
    except: return ""

def save_interaction(user_id, u_msg, b_msg):
    if users_col is None: return
    try:
        users_col.update_one({"_id": user_id}, 
            {"$push": {"history": {"user": u_msg, "bot": b_msg, "time": datetime.now()}}, 
             "$setOnInsert": {"joined": datetime.now()}}, upsert=True)
    except: pass
