from pymongo import MongoClient
import os

client = MongoClient("mongodb://localhost:27017/")
db = client["interhack"]
collection = db["daily_alerts"]

count = collection.count_documents({})
print(f"Total documents in daily_alerts: {count}")

if count > 0:
    first = collection.find_one({})
    print(f"First document keys: {list(first.keys())}")
    print(f"First document Priority_Score: {first.get('Priority_Score')}")

metadata = db["metadata"].find_one({"_id": "last_loaded"})
print(f"Metadata last_loaded: {metadata}")
