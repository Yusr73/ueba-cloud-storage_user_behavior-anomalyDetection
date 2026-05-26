import json
from datetime import datetime, timezone
from models.database import get_db
import os

def write_log(event_type: str, uid: str, uid_type: str, params: dict,
              is_local_ip: bool = True, role: str = None, location: dict = None,
              ip_address: str = None, user_agent: str = None):
    
    log_entry = {
        "time": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "uid": uid,
        "uidType": uid_type,
        "type": event_type,
        "params": params,
        "isLocalIP": is_local_ip,
        "role": role,
        "location": location,
        "ipAddress": ip_address,
        "userAgent": user_agent
    }
    
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs (time, uid, uid_type, type, params, is_local_ip, role, location, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.fromisoformat(log_entry['time'].replace('Z', '+00:00')),
            log_entry['uid'],
            log_entry['uidType'],
            log_entry['type'],
            json.dumps(log_entry['params']),
            log_entry['isLocalIP'],
            log_entry['role'],
            json.dumps(log_entry['location']) if log_entry['location'] else None,
            log_entry['ipAddress'],
            log_entry['userAgent']
        ))
        conn.commit()
        cur.close()
        conn.close()
        
        with open("/app/logs/logs.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Erreur log: {e}")