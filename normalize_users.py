# normalize_users.py
from pymongo import MongoClient
import time

# MongoDB connection (reuse your bot's MongoDB URL)
MONGO_URL = "mongodb+srv://aarshhub:6L1PAPikOnAIHIRA@cluster0.6shiu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo = MongoClient(MONGO_URL)
db = mongo["VideoBot"]
users_collection = db["users"]

DEFAULT_FIELDS = {
    "videos_sent": 0,
    "bonus_quota_used": 0,
    "quota_reset_time": time.time() + 86400,
    "premium_expiry": None,
}

def normalize_all_users():
    users = users_collection.find()
    updated_count = 0

    for user in users:
        updates = {}
        for field, default_value in DEFAULT_FIELDS.items():
            if field not in user:
                updates[field] = default_value

        if updates:
            users_collection.update_one({"id": user["id"]}, {"$set": updates})
            updated_count += 1

    return updated_count
