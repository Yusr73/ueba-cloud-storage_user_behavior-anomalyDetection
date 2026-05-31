import json
from datetime import datetime, timezone
from models.database import get_db
import os
from services.realtime_detection import RealtimeDetection

def write_log(event_type: str, uid: str, uid_type: str, params: dict,
              is_local_ip: bool = True, role: str = None, location: dict = None):
    
    log_entry = {
        "time": datetime.now(timezone.utc),
        "uid": uid,
        "uid_type": uid_type,
        "type": event_type,
        "params": params,
        "is_local_ip": is_local_ip,
        "role": role,
        "location": location
    }
    
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO logs (time, uid, uid_type, type, params, is_local_ip, role, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            log_entry['time'],
            log_entry['uid'],
            log_entry['uid_type'],
            log_entry['type'],
            json.dumps(log_entry['params']),
            log_entry['is_local_ip'],
            log_entry['role'],
            json.dumps(log_entry['location']) if log_entry['location'] else None
        ))
        result = cur.fetchone()
        log_id = result['id']
        conn.commit()
        cur.close()
        conn.close()
        
        # ============================================
        # REAL-TIME DETECTION TRIGGER
        # ============================================
        # Trigger real-time detection on every log write
        event_time = log_entry['time']
        
        # Check sliding window events (ransomware, mass deletion, malicious upload)
        if event_type in ['file_written', 'file_deleted', 'file_created']:
            RealtimeDetection.check_event(uid, event_type, event_time)
        
        # Track logins for account takeover detection
        if event_type == 'login_successful':
            RealtimeDetection.on_login_success(uid, event_time)
        
        # Check access after login for account takeover
        if event_type == 'file_accessed':
            RealtimeDetection.check_access_after_login(uid, event_time)
        
        # Convertir datetime en ISO
        log_json = {
            "id": log_id,
            "time": log_entry['time'].isoformat().replace('+00:00', 'Z'),
            "uid": log_entry['uid'],
            "uid_type": log_entry['uid_type'],
            "type": log_entry['type'],
            "params": log_entry['params'],
            "is_local_ip": log_entry['is_local_ip'],
            "role": log_entry['role'],
            "location": log_entry['location']
        }
        
        os.makedirs("/app/logs", exist_ok=True)
        with open("/app/logs/logs.json", "a") as f:
            f.write(json.dumps(log_json) + "\n")
            
    except Exception as e:
        print(f"Erreur log: {e}")