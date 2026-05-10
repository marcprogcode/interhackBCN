import os
import json
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import uvicorn
from datetime import datetime, timedelta
from pydantic import BaseModel

app = FastAPI(title="Interhack BCN Daily Alerts API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            # Check if alert_id field exists (to handle migration)
            if collection.find_one({"alert_id": {"$exists": False}}):
                print("Found old records missing 'alert_id'. Forcing reload...")
                load_data_to_mongo(force=True)
                return

            metadata_collection = db["metadata"]
            last_loaded_doc = metadata_collection.find_one({"_id": "last_loaded"})
            if last_loaded_doc and "timestamp" in last_loaded_doc:
                last_loaded_time = last_loaded_doc["timestamp"]
                if datetime.now() - last_loaded_time < timedelta(minutes=20):
                    print("Data already exists and is fresh. Using cached data.")
                    return
            print("Data is stale or missing timestamp, proceeding to load.")

        if os.path.exists(CSV_PATH) or force:
            # 1. Trigger the actual Recalculation Engine
            print("Triggering Prioritization Engine recalculation...")
            from prioritization_engine import PrioritizationEngine
            engine = PrioritizationEngine()
            engine.generate_alerts() # This updates the CSV with fresh logic
            
            # 2. Prepare for MongoDB Load
            from data_loader import DataLoader
            loader = DataLoader()
            locations = loader.get_client_locations()
            
            df = pd.read_csv(CSV_PATH)
            
            # Map locations and rename/normalize fields
            df['location'] = df['Client_ID'].map(locations).fillna("Unknown")
            
            # Normalize Priority_Score to 1-10 scale using quantiles for better distribution
            if not df.empty and 'Priority_Score' in df.columns:
                # Use a log transformation to dampen outliers before scaling
                df['log_score'] = np.log1p(df['Priority_Score'])
                min_s = df['log_score'].min()
                max_s = df['log_score'].max()
                if max_s > min_s:
                    df['priority_score'] = 1 + 9 * (df['log_score'] - min_s) / (max_s - min_s)
                else:
                    df['priority_score'] = 5.0
            
            # Prepare final documents for MongoDB
            records = []
            for _, row in df.iterrows():
                record = {
                    "company_id": str(row['Client_ID']),
                    "alert_id": f"{str(row['Client_ID'])}_{row.get('Product_Family', 'N/A')}_{row.get('Type', 'N/A')}".replace(" ", "_"),
                    "location": row['location'],
                    "reason": row['Reason'],
                    "priority_score": round(float(row.get('priority_score', 5.0)), 1),
                    "expected_return": round(float(row.get('Expected_Value', 0.0)), 2),
                    "confidence": round(float(row.get('Confidence', 0.5)), 2),
                    "product_family": row.get('Product_Family', 'N/A'),
                    "type": row.get('Type', 'N/A')
                }
                
                if 'Interpretability_JSON' in row and pd.notna(row['Interpretability_JSON']):
                    try:
                        record["interpretability"] = json.loads(row['Interpretability_JSON'])
                    except json.JSONDecodeError:
                        pass
                        
                records.append(record)
            
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

class StatusUpdate(BaseModel):
    status: str

@app.put("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, update: StatusUpdate):
    if update.status not in ["new", "wip", "complete", "discarded"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    status_collection = db["alert_statuses"]
    
    if update.status == "new":
        status_collection.delete_one({"alert_id": alert_id})
    else:
        status_collection.update_one(
            {"alert_id": alert_id},
            {"$set": {"status": update.status, "updated_at": datetime.now()}},
            upsert=True
        )
    return {"message": "Status updated successfully", "status": update.status}

@app.get("/api/alerts")
@app.get("/alerts")
def get_alerts(skip: int = 0, limit: int = 20, filter: str = "all"):
    try:
        # Check connection
        client.admin.command('ping')
        
        # Check when data was loaded for the last time
        metadata_collection = db["metadata"]
        last_loaded_doc = metadata_collection.find_one({"_id": "last_loaded"})
        
        if not last_loaded_doc or "timestamp" not in last_loaded_doc or (datetime.now() - last_loaded_doc["timestamp"]) > timedelta(minutes=20):
            print("Data is older than 20 minutes or not found. Reloading data...")
            load_data_to_mongo(force=True)
        
        # Build query based on filter and alert statuses
        status_collection = db["alert_statuses"]
        
        # Fetch statuses to filter in-memory or via join (Mongo join is complex here, let's use a query on statuses)
        query = {}
        
        if filter == "done":
            done_ids = [doc["alert_id"] for doc in status_collection.find({"status": "complete"}) if "alert_id" in doc]
            query = {"alert_id": {"$in": done_ids}}
        elif filter == "discarded":
            disc_ids = [doc["alert_id"] for doc in status_collection.find({"status": "discarded"}) if "alert_id" in doc]
            query = {"alert_id": {"$in": disc_ids}}
        elif filter == "wip":
            wip_ids = [doc["alert_id"] for doc in status_collection.find({"status": "wip"}) if "alert_id" in doc]
            query = {"alert_id": {"$in": wip_ids}}
        else:
            # "all" or "urgent" - exclude completed and discarded
            excluded_ids = [doc["alert_id"] for doc in status_collection.find({"status": {"$in": ["complete", "discarded"]}}) if "alert_id" in doc]
            if excluded_ids:
                query = {"alert_id": {"$nin": excluded_ids}}
            
            if filter == "urgent":
                query["priority_score"] = {"$gte": 7.0}

        # Retrieve documents from the collection
        print(f"DEBUG: get_alerts(skip={skip}, limit={limit}, filter={filter})")
        cursor = collection.find(query, {"_id": 0, "interpretability": 0}).sort([("priority_score", -1), ("alert_id", 1)]).skip(skip).limit(limit)
        alerts = list(cursor)
        print(f"DEBUG: Returning {len(alerts)} alerts")
        
        # Join statuses
        statuses = {doc["alert_id"]: doc["status"] for doc in status_collection.find() if "alert_id" in doc}
        
        for alert in alerts:
            # Ensure alert_id is present (should be from records)
            if "alert_id" not in alert:
                 alert["alert_id"] = f"{alert.get('company_id')}_{alert.get('product_family', 'N/A')}_{alert.get('type', 'N/A')}".replace(" ", "_")
            alert["status"] = statuses.get(alert["alert_id"], "new")
            
        return alerts
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="MongoDB service is unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts/{alert_id}/interpretability")
def get_interpretability(alert_id: str):
    try:
        # Check connection
        client.admin.command('ping')
        
        # Check when data was loaded for the last time
        metadata_collection = db["metadata"]
        last_loaded_doc = metadata_collection.find_one({"_id": "last_loaded"})
        
        if not last_loaded_doc or "timestamp" not in last_loaded_doc or (datetime.now() - last_loaded_doc["timestamp"]) > timedelta(minutes=20):
            print("Data is older than 20 minutes or not found. Reloading data...")
            load_data_to_mongo(force=True)
            
        alert = collection.find_one({"alert_id": alert_id}, {"_id": 0, "interpretability": 1})
        # Try finding by company_id fallback if the previous didn't work (for backwards compatibility if needed, though we reload on empty)
        if not alert:
             alert = collection.find_one({"company_id": alert_id}, {"_id": 0, "interpretability": 1})
             
        if alert and "interpretability" in alert:
            return alert["interpretability"]
        else:
            raise HTTPException(status_code=404, detail="Interpretability data not found for this alert")
            
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="MongoDB service is unavailable")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
