import sys
import os

# Ensure the current directory and its parent (root) are in the path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Query
import pandas as pd
from prioritization_engine import PrioritizationEngine
import uvicorn

app = FastAPI(title="Interhack BCN Retention API")
engine = PrioritizationEngine()

@app.get("/alerts")
async def get_alerts(top_x: int = Query(10, description="Number of top priority alerts to fetch")):
    # Generate alerts using the engine
    alerts_df = engine.generate_alerts()
    
    if alerts_df.empty:
        return []
    
    # Take top X
    top_alerts = alerts_df.head(top_x).copy()
    
    # Get client locations for joining
    locations = engine.loader.get_client_locations()
    top_alerts['Location'] = top_alerts['Client_ID'].map(locations).fillna("Unknown")
    
    # Normalize priority score 1-10 within the selection
    max_score = top_alerts['Priority_Score'].max()
    min_score = top_alerts['Priority_Score'].min()
    
    if max_score > min_score:
        top_alerts['Normalized_Score'] = ((top_alerts['Priority_Score'] - min_score) / (max_score - min_score) * 9 + 1).round(1)
    else:
        top_alerts['Normalized_Score'] = 10.0
        
    # Format the response as requested
    result = []
    for _, row in top_alerts.iterrows():
        result.append({
            "company_id": str(row['Client_ID']),
            "location": str(row['Location']),
            "reason": str(row['Reason']),
            "priority_score": float(row['Normalized_Score']),
            "expected_return": float(round(row['Expected_Value'], 2)),
            "confidence": float(round(row['Confidence'], 2))
        })
        
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
