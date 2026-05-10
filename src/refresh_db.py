"""
Refresh DB — re-runs the prioritization engine and force-reloads
the results into MongoDB, bypassing the staleness cache.

Usage:
    python src/refresh_db.py
"""

import sys
import os
import time

# Ensure src/ is on the path so local imports work
sys.path.insert(0, os.path.dirname(__file__))

from prioritization_engine import PrioritizationEngine
from api import load_data_to_mongo

def main():
    start = time.time()

    print("=" * 60)
    print("  REFRESH DB — Full Recalculation + MongoDB Reload")
    print("=" * 60)

    # Step 1: Re-run the prioritization engine (writes outputs/daily_alerts.csv)
    print("\n[1/2] Running prioritization engine...")
    engine = PrioritizationEngine()
    alerts_df = engine.generate_alerts()

    if alerts_df.empty:
        print("⚠  Engine produced zero alerts. MongoDB will NOT be updated.")
        return

    # Step 2: Force-reload into MongoDB (bypasses the 20-min cache)
    print("\n[2/2] Force-loading into MongoDB...")
    load_data_to_mongo(force=True)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  Done — {len(alerts_df)} alerts refreshed in {elapsed:.1f}s")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
