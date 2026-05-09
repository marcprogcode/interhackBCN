import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import uvicorn
from datetime import datetime, timedelta

app = FastAPI(title="Interhack BCN Daily Alerts API")

# Connect to local MongoDB instance
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# Set a low timeout so it doesn't hang if Mongo isn't running
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
db = client["interhack"]
collection = db["daily_alerts"]

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'daily_alerts.csv')

def load_data_to_mongo(force=False):
    try:
        # Check connection first
        client.admin.command('ping')
        
        # If not forcing and we already have data, treat it as a cache
        if not force and collection.count_documents({}) > 0:
            metadata_collection = db["metadata"]
            last_loaded_doc = metadata_collection.find_one({"_id": "last_loaded"})
            if last_loaded_doc and "timestamp" in last_loaded_doc:
                last_loaded_time = last_loaded_doc["timestamp"]
                if datetime.now() - last_loaded_time < timedelta(minutes=20):
                    print("Data already exists and is fresh. Using cached data.")
                    return
            print("Data is stale or missing timestamp, proceeding to load.")

        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            # Convert dataframe to list of dictionaries
            records = df.to_dict(orient='records')
            
            # Clear existing data and insert new data
            collection.delete_many({})
            if records:
                collection.insert_many(records)
                print(f"Successfully loaded {len(records)} records into MongoDB.")
                # Store the time it stored the data
                db["metadata"].update_one(
                    {"_id": "last_loaded"},
                    {"$set": {"timestamp": datetime.now()}},
                    upsert=True
                )
            else:
                print("CSV file is empty.")
        else:
            print(f"CSV file not found at {CSV_PATH}")

    except ServerSelectionTimeoutError:
        print("MongoDB is not running or unreachable. Please start MongoDB.")
    except Exception as e:
        print(f"Error loading CSV to MongoDB: {e}")

# Load the data when the script starts (only if MongoDB is empty)
load_data_to_mongo()

@app.get("/api/alerts")
def get_all_alerts():
    try:
        # Check connection
        client.admin.command('ping')
        
        # Check when data was loaded for the last time
        metadata_collection = db["metadata"]
        last_loaded_doc = metadata_collection.find_one({"_id": "last_loaded"})
        
        if not last_loaded_doc or "timestamp" not in last_loaded_doc or (datetime.now() - last_loaded_doc["timestamp"]) > timedelta(minutes=20):
            print("Data is older than 20 minutes or not found. Reloading data...")
            load_data_to_mongo(force=True)
        
        # Retrieve all documents from the collection
        cursor = collection.find({})
        alerts = []
        for document in cursor:
            # Convert ObjectId to string or remove it
            document['_id'] = str(document['_id'])
            alerts.append(document)
        return {"data": alerts}
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="MongoDB service is unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
