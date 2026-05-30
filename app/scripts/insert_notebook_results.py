#!/usr/bin/env python3
"""
Directly insert the notebook results into daily_anomalies table
No recalculation - just using the proven notebook outputs
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database import get_db
from datetime import datetime

# Results directly from the notebook analysis
ALICE_FLAGGED_DAYS = [
    # date, attack_type, baseline_score, confidence, analyst_notes
    ("2017-07-17", "DATA_THEFT", 23.34, "HIGH", "Data theft detected - high volume file access on unique paths"),
    ("2017-07-28", "DATA_THEFT", 15.18, "HIGH", "Data theft detected - high volume file access on unique paths"),
    ("2017-08-24", "DATA_THEFT", 2.99, "MEDIUM", "Data theft detected - elevated file access"),
    ("2017-08-01", "DIRECTORY_TRAVERSAL", 2.00, "MEDIUM", "Unusual directory exploration pattern - unique_dir1 spike"),
    ("2017-07-15", "BOT_OR_MASS_ACTIVITY", 0.85, "MEDIUM", "Massive event volume across few hours"),
    ("2017-09-18", "OFF_HOURS", 0.70, "MEDIUM", "Unusual activity during night hours"),
    ("2017-07-08", "LOGIN_ACTIVITY", 0.68, "MEDIUM", "Spike in login attempts - all successful, busy day"),
    ("2017-08-08", "DIVERSE_ACTIVITY", 0.60, "MEDIUM", "Wide variety of event types"),
    ("2017-07-20", "UNKNOWN", 0.55, "MEDIUM", "Unclassified - file_events and path_depth_mean spikes"),
    ("2017-10-02", "PATH_REUSE_ANOMALY", 0.50, "MEDIUM", "Unusual path access pattern"),
    ("2017-08-22", "OFF_HOURS", 0.30, "MEDIUM", "Unusual activity during night hours"),
    ("2017-07-16", "UNKNOWN", 0.26, "MEDIUM", "Unclassified - path_reuse_ratio and active_hours spikes"),
    ("2017-07-14", "LOGIN_ACTIVITY", 0.25, "MEDIUM", "Spike in login attempts - busy day"),
    ("2017-10-03", "DATA_THEFT", 0.22, "MEDIUM", "Data theft detected - elevated file access"),
    ("2017-09-14", "DIVERSE_ACTIVITY", 0.20, "MEDIUM", "Wide variety of event types"),
    ("2017-07-10", "LOGIN_ACTIVITY", 0.13, "MEDIUM", "Spike in login attempts"),
    ("2017-07-27", "UNKNOWN", 0.09, "MEDIUM", "Unclassified - unique_paths spike"),
    ("2017-08-21", "OFF_HOURS", 0.07, "MEDIUM", "Unusual activity during night hours"),
    ("2017-07-09", "PATH_REUSE_ANOMALY", 0.07, "MEDIUM", "Unusual path access pattern"),
    ("2017-09-21", "OFF_HOURS", 0.02, "MEDIUM", "Unusual activity during night hours"),
    ("2017-08-28", "OFF_HOURS", 0.001, "MEDIUM", "Unusual activity during night hours"),
]

BOB_FLAGGED_DAYS = [
    # date, attack_type, baseline_score, confidence, analyst_notes
    ("2017-07-11", "DATA_THEFT", 72.79, "HIGH", "Massive data theft - 7525 events, 7408 unique paths"),
    ("2017-08-18", "DIRECTORY_TRAVERSAL", 14.17, "HIGH", "Unusual directory exploration - login spike followed by traversal"),
    ("2017-07-23", "DIRECTORY_TRAVERSAL", 2.57, "MEDIUM", "Directory traversal - unique_dir1 spike to 25"),
    ("2017-08-24", "DATA_THEFT", 1.62, "MEDIUM", "Data theft - 876 events, 531 unique paths"),
    ("2017-07-17", "DIRECTORY_TRAVERSAL", 1.55, "MEDIUM", "Directory traversal - unique_dir2 spike to 28"),
    ("2017-08-30", "UNKNOWN", 1.02, "MEDIUM", "Unclassified - path_reuse_ratio and active_hours spikes"),
    ("2017-07-14", "DIRECTORY_TRAVERSAL", 0.88, "MEDIUM", "Directory traversal - unique_dir2 spike to 31"),
    ("2017-07-21", "DIRECTORY_TRAVERSAL", 0.80, "MEDIUM", "Directory traversal - unique_dir2 spike to 28"),
    ("2017-09-13", "LOGIN_ACTIVITY", 0.55, "MEDIUM", "Login activity spike"),
    ("2017-10-02", "OFF_HOURS", 0.53, "MEDIUM", "Unusual night activity - 100% night fraction"),
    ("2017-08-11", "OFF_HOURS", 0.53, "MEDIUM", "Unusual night activity - 100% night fraction"),
    ("2017-08-22", "DATA_THEFT", 0.46, "MEDIUM", "Data theft - 683 events, 404 unique paths"),
    ("2017-07-10", "UNKNOWN", 0.39, "MEDIUM", "Unclassified - path_depth_mean and unique_paths spikes"),
    ("2017-09-05", "UNKNOWN", 0.30, "MEDIUM", "Unclassified - file_events, events_total spikes"),
    ("2017-07-12", "LOGIN_ACTIVITY", 0.22, "MEDIUM", "Login activity spike"),
    ("2017-09-02", "UNKNOWN", 0.13, "MEDIUM", "Unclassified - active_hours spike"),
    ("2017-09-04", "UNKNOWN", 0.13, "MEDIUM", "Unclassified - active_hours spike"),
    ("2017-07-16", "OFF_HOURS", 0.12, "MEDIUM", "Night activity - 73% night fraction"),
    ("2017-08-04", "OFF_HOURS", 0.11, "MEDIUM", "Night activity - 73% night fraction"),
    ("2017-08-15", "PATH_REUSE_ANOMALY", 0.10, "MEDIUM", "Unusual path reuse pattern"),
    ("2017-09-23", "PATH_REUSE_ANOMALY", 0.10, "MEDIUM", "Unusual path reuse pattern"),
    ("2017-09-24", "PATH_REUSE_ANOMALY", 0.10, "MEDIUM", "Unusual path reuse pattern"),
    ("2017-08-26", "UNKNOWN", 0.08, "MEDIUM", "Unclassified - login_successful and login_success_rate spikes"),
    ("2017-09-03", "PATH_REUSE_ANOMALY", 0.08, "MEDIUM", "Unusual path reuse pattern"),
    ("2017-08-01", "OFF_HOURS", 0.05, "MEDIUM", "Unusual night activity"),
    ("2017-07-31", "DIRECTORY_TRAVERSAL", 0.04, "MEDIUM", "Directory traversal"),
]

def insert_results():
    print("="*60)
    print("INSERTING NOTEBOOK RESULTS INTO daily_anomalies")
    print("="*60)
    
    conn = get_db()
    cur = conn.cursor()
    
    # Clear existing data for alice and bob
    cur.execute("DELETE FROM daily_anomalies WHERE user_id IN ('alice', 'bob')")
    print("Cleared existing alice/bob records")
    
    # Insert Alice's flagged days
    print(f"\nInserting {len(ALICE_FLAGGED_DAYS)} days for alice...")
    for date_str, attack_type, score, confidence, notes in ALICE_FLAGGED_DAYS:
        cur.execute("""
            INSERT INTO daily_anomalies 
            (date, user_id, baseline_score, flagged_by_baseline, attack_type, confidence, analyst_notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (date_str, 'alice', score, True, attack_type, confidence, notes))
        print(f"  {date_str}: {attack_type} (score={score})")
    
    # Insert Bob's flagged days
    print(f"\nInserting {len(BOB_FLAGGED_DAYS)} days for bob...")
    for date_str, attack_type, score, confidence, notes in BOB_FLAGGED_DAYS:
        cur.execute("""
            INSERT INTO daily_anomalies 
            (date, user_id, baseline_score, flagged_by_baseline, attack_type, confidence, analyst_notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (date_str, 'bob', score, True, attack_type, confidence, notes))
        print(f"  {date_str}: {attack_type} (score={score})")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print("INSERT COMPLETE")
    print("="*60)
    
    # Verify
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, COUNT(*) FROM daily_anomalies GROUP BY user_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    print("\nFinal counts in database:")
    for row in rows:
        print(f"  {row['user_id']}: {row['count']} flagged days")

if __name__ == "__main__":
    insert_results()