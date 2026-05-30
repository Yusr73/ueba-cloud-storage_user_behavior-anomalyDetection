"""
Real-Time Detection Service - Sliding Window Anomaly Detection
Triggered on every log write, independent from daily batch analysis

Sliding Windows:
- Ransomware: file_written events in 60 seconds
- Mass Deletion: file_deleted events in 300 seconds
- Malicious Upload: file_created events in 300 seconds
- Account Takeover: file_accessed events within 60 seconds after login_successful
"""

import json
from collections import deque
from datetime import datetime, timezone, timedelta
from models.database import get_db

class RealtimeDetection:
    
    # In-memory sliding windows per user
    _windows = {}
    
    # Cache for historical maximums (queried once per user per event type)
    _historical_max_cache = {}
    
    # Multipliers based on user profile
    USER_MULTIPLIERS = {
        'alice': 2,
        'bob': 3,
        'spectacular-copper-cheetah-postman': 2,
        'ready-silver-angelfish-quarryworker': 3,
    }
    
    # Window definitions: (event_type, window_seconds, alert_name)
    WINDOW_CONFIGS = [
        ('file_written', 60, 'Ransomware'),
        ('file_deleted', 300, 'Mass Deletion'),
        ('file_created', 300, 'Malicious Upload'),
    ]
    
    @classmethod
    def _get_window_key(cls, user_id, event_type):
        """Generate cache key for a user's sliding window"""
        return f"{user_id}_{event_type}"
    
    @classmethod
    def _get_historical_max(cls, user_id, event_type):
        """Get historical maximum count for a user-event type (cached)"""
        cache_key = cls._get_window_key(user_id, event_type)
        
        if cache_key in cls._historical_max_cache:
            return cls._historical_max_cache[cache_key]
        
        conn = get_db()
        cur = conn.cursor()
        
        # Get the maximum count in any window from historical data (excluding today)
        if event_type == 'file_written':
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM logs
                WHERE uid = %s AND type = %s AND time < CURRENT_DATE
                GROUP BY DATE_TRUNC('minute', time)
                ORDER BY cnt DESC
                LIMIT 1
            """, (user_id, event_type))
        elif event_type in ['file_deleted', 'file_created']:
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM logs
                WHERE uid = %s AND type = %s AND time < CURRENT_DATE
                GROUP BY DATE_TRUNC('hour', time), (EXTRACT(MINUTE FROM time)::INT / 5)
                ORDER BY cnt DESC
                LIMIT 1
            """, (user_id, event_type))
        else:
            cur.close()
            conn.close()
            return 0
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        historical_max = row['cnt'] if row else 0
        cls._historical_max_cache[cache_key] = historical_max
        print(f"Historical max for {user_id}/{event_type}: {historical_max}")
        
        return historical_max
    
    @classmethod
    def _get_login_sequence_historical_max(cls, user_id):
        """Get historical max for login sequence (accesses after login)"""
        cache_key = f"{user_id}_login_sequence"
        
        if cache_key in cls._historical_max_cache:
            return cls._historical_max_cache[cache_key]
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM logs l1
            JOIN logs l2 ON l2.uid = l1.uid
            WHERE l1.uid = %s 
            AND l1.type = 'login_successful'
            AND l2.type = 'file_accessed'
            AND l2.time > l1.time
            AND l2.time < l1.time + interval '1 minute'
            AND l1.time < '2018-01-01'
            GROUP BY l1.time
            ORDER BY cnt DESC
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        historical_max = row['cnt'] if row else 0
        cls._historical_max_cache[cache_key] = historical_max
        print(f"Historical max for {user_id}/login_sequence: {historical_max}")
        
        return historical_max
    
    @classmethod
    def _get_multiplier(cls, user_id):
        """Get multiplier for user based on profile"""
        return cls.USER_MULTIPLIERS.get(user_id, 3)
    
    @classmethod
    def check_event(cls, user_id, event_type, event_time):
        """
        Check if a single event triggers an alert
        Called from logger.py on every log write
        """
        # Find matching window config
        config = None
        for et, ws, name in cls.WINDOW_CONFIGS:
            if et == event_type:
                config = (et, ws, name)
                break
        
        if not config:
            return None
        
        event_type, window_seconds, alert_name = config
        
        # Initialize and clean window
        key = cls._get_window_key(user_id, event_type)
        if key not in cls._windows:
            cls._windows[key] = deque()
        
        # Add current event to window
        cls._windows[key].append(event_time)
        
        # Clean old events
        while cls._windows[key] and (event_time - cls._windows[key][0]).total_seconds() > window_seconds:
            cls._windows[key].popleft()
        
        current_count = len(cls._windows[key])
        
        # Get historical max and multiplier
        historical_max = cls._get_historical_max(user_id, event_type)
        multiplier = cls._get_multiplier(user_id)
        threshold = historical_max * multiplier if historical_max > 0 else 1
        
        # Check if threshold exceeded
        if current_count > threshold and threshold > 0:
            cls._store_alert(
                user_id=user_id,
                event_type=event_type,
                window_type=f"{window_seconds}s_window",
                detected_at=event_time,
                count_value=current_count,
                threshold_value=threshold,
                multiplier=multiplier,
                details={
                    "historical_max": historical_max,
                    "window_seconds": window_seconds,
                    "alert_name": alert_name
                }
            )
            
            return {
                "alert": True,
                "event_type": event_type,
                "alert_name": alert_name,
                "count": current_count,
                "threshold": threshold,
                "multiplier": multiplier,
                "window_seconds": window_seconds
            }
        
        return None
    
    @classmethod
    def on_login_success(cls, user_id, login_time):
        """
        Track login for account takeover detection
        Account Takeover: file_accessed within 60 seconds after login
        """
        key = f"{user_id}_logins"
        if key not in cls._windows:
            cls._windows[key] = deque()
        
        cls._windows[key].append(login_time)
        
        # Initialize counter for this login
        counter_key = f"{user_id}_login_counter_{login_time.timestamp()}"
        cls._windows[counter_key] = 0
        
        # Clean old logins (> 60 seconds)
        now = datetime.now(timezone.utc)
        while cls._windows[key] and (now - cls._windows[key][0]).total_seconds() > 60:
            old_login = cls._windows[key].popleft()
            old_counter_key = f"{user_id}_login_counter_{old_login.timestamp()}"
            if old_counter_key in cls._windows:
                del cls._windows[old_counter_key]
        
        print(f"Login tracked for {user_id} at {login_time}. Active logins: {len(cls._windows[key])}")
    
    @classmethod
    def check_access_after_login(cls, user_id, access_time):
        """
        Check if a file_access occurred shortly after a login
        Called on file_accessed events
        """
        login_key = f"{user_id}_logins"
        
        if login_key not in cls._windows or not cls._windows[login_key]:
            return None
        
        alerts = []
        
        # Check each active login
        for login_time in list(cls._windows[login_key]):
            if (access_time - login_time).total_seconds() <= 60:
                # Increment counter for this login
                counter_key = f"{user_id}_login_counter_{login_time.timestamp()}"
                if counter_key not in cls._windows:
                    cls._windows[counter_key] = 0
                
                cls._windows[counter_key] += 1
                current_count = cls._windows[counter_key]
                
                # Get historical max and threshold
                historical_max = cls._get_login_sequence_historical_max(user_id)
                multiplier = cls._get_multiplier(user_id)
                threshold = historical_max * multiplier if historical_max > 0 else 1
                
                print(f"Login at {login_time}: access #{current_count} (threshold={threshold})")
                
                # Check if threshold exceeded
                if current_count > threshold and threshold > 0:
                    # Check if we already alerted for this login
                    alert_key = f"{user_id}_alert_{login_time.timestamp()}"
                    if alert_key not in cls._windows:
                        cls._windows[alert_key] = True
                        
                        cls._store_alert(
                            user_id=user_id,
                            event_type="account_takeover",
                            window_type="60s_after_login",
                            detected_at=access_time,
                            count_value=current_count,
                            threshold_value=threshold,
                            multiplier=multiplier,
                            details={
                                "historical_max": historical_max,
                                "login_time": login_time.isoformat(),
                                "alert_name": "Account Takeover"
                            }
                        )
                        
                        print(f"✅ ACCOUNT TAKEOVER ALERT: {current_count} accesses (threshold={threshold})")
                        alerts.append(True)
        
        if alerts:
            return {"alert": True, "event_type": "account_takeover", "count": len(alerts)}
        
        return None
    
    @classmethod
    def _store_alert(cls, user_id, event_type, window_type, detected_at, 
                      count_value, threshold_value, multiplier, details):
        """Store alert in database (1-week sliding window)"""
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO rare_events_alerts 
            (user_id, event_type, window_type, detected_at, 
             count_value, threshold_value, multiplier, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, event_type, window_type, detected_at,
              count_value, threshold_value, multiplier,
              json.dumps(details)))
        conn.commit()
        cur.close()
        conn.close()
        print(f"REAL-TIME ALERT STORED: {user_id} - {event_type} - {count_value} events (threshold: {threshold_value})")
    
    @classmethod
    def get_recent_alerts(cls, user_id=None, hours=24):
        """Get recent alerts from database"""
        conn = get_db()
        cur = conn.cursor()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        if user_id:
            cur.execute("""
                SELECT * FROM rare_events_alerts 
                WHERE user_id = %s AND detected_at >= %s
                ORDER BY detected_at DESC
                LIMIT 100
            """, (user_id, cutoff))
        else:
            cur.execute("""
                SELECT * FROM rare_events_alerts 
                WHERE detected_at >= %s
                ORDER BY detected_at DESC
                LIMIT 100
            """, (cutoff,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        alerts = []
        for row in rows:
            alerts.append({
                "id": row['id'],
                "user_id": row['user_id'],
                "event_type": row['event_type'],
                "window_type": row['window_type'],
                "detected_at": row['detected_at'].isoformat(),
                "count_value": row['count_value'],
                "threshold_value": row['threshold_value'],
                "multiplier": row['multiplier'],
                "details": row['details']
            })
        return alerts