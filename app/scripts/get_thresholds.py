import sys
sys.path.insert(0, '/app')

from models.database import get_db
from datetime import datetime

def get_max(uid, query_type):
    conn = get_db()
    cur = conn.cursor()
    
    if query_type == 'file_written_minute':
        cur.execute("""
            SELECT COUNT(*) as cnt FROM logs 
            WHERE uid = %s AND type = 'file_written' AND time < '2018-01-01'
            GROUP BY DATE_TRUNC('minute', time) 
            ORDER BY cnt DESC LIMIT 1
        """, (uid,))
    elif query_type == 'file_accessed_minute':
        cur.execute("""
            SELECT COUNT(*) as cnt FROM logs 
            WHERE uid = %s AND type = 'file_accessed' AND time < '2018-01-01'
            GROUP BY DATE_TRUNC('minute', time) 
            ORDER BY cnt DESC LIMIT 1
        """, (uid,))
    elif query_type == 'unique_paths_day':
        cur.execute("""
            SELECT COUNT(DISTINCT params->>'path') as cnt FROM logs 
            WHERE uid = %s AND time < '2018-01-01'
            GROUP BY DATE_TRUNC('day', time) 
            ORDER BY cnt DESC LIMIT 1
        """, (uid,))
    elif query_type == 'login_attempt_day':
        cur.execute("""
            SELECT COUNT(*) as cnt FROM logs 
            WHERE uid = %s AND type = 'login_attempt' AND time < '2018-01-01'
            GROUP BY DATE_TRUNC('day', time) 
            ORDER BY cnt DESC LIMIT 1
        """, (uid,))
    elif query_type == 'events_total_day':
        cur.execute("""
            SELECT COUNT(*) as cnt FROM logs 
            WHERE uid = %s AND time < '2018-01-01'
            GROUP BY DATE_TRUNC('day', time) 
            ORDER BY cnt DESC LIMIT 1
        """, (uid,))
    else:
        return 0
    
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row['cnt'] if row else 0

print("="*60)
print("ALICE THRESHOLDS (Historical Max from 2017 data)")
print("="*60)
print(f"file_written (per minute max): {get_max('alice', 'file_written_minute')}")
print(f"unique_paths (per day max): {get_max('alice', 'unique_paths_day')}")
print(f"login_attempt (per day max): {get_max('alice', 'login_attempt_day')}")
print(f"events_total (per day max): {get_max('alice', 'events_total_day')}")

print("\n" + "="*60)
print("BOB THRESHOLDS (Historical Max from 2017 data)")
print("="*60)
print(f"file_written (per minute max): {get_max('bob', 'file_written_minute')}")
print(f"unique_paths (per day max): {get_max('bob', 'unique_paths_day')}")
print(f"login_attempt (per day max): {get_max('bob', 'login_attempt_day')}")
print(f"events_total (per day max): {get_max('bob', 'events_total_day')}")