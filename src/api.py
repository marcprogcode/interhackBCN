import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import uvicorn

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
            print("Data already exists in MongoDB. Using cached data.")
            return

        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)
            # Convert dataframe to list of dictionaries
            records = df.to_dict(orient='records')
            
            # Clear existing data and insert new data
            collection.delete_many({})
            if records:
                collection.insert_many(records)
                print(f"Successfully loaded {len(records)} records into MongoDB.")
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
