import psycopg2
import psycopg2.extras
from config import Config
from datetime import datetime, timezone, timedelta
import json

def get_db():
    return psycopg2.connect(
        host=Config.DB_HOST,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def init_database():
    conn = get_db()
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            uid VARCHAR(255) UNIQUE,
            username VARCHAR(100) UNIQUE,
            email VARCHAR(255),
            hashed_password VARCHAR(255),
            role VARCHAR(50),
            created_at TIMESTAMP
        )
    """)
    
    # Logs table - EXACTEMENT 8 colonnes (format CLUE)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            time TIMESTAMP,
            uid VARCHAR(255),
            uid_type VARCHAR(50),
            type VARCHAR(100),
            params JSONB,
            is_local_ip BOOLEAN,
            role VARCHAR(50),
            location JSONB
        )
    """)
    
    # Files table (for tracking)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255),
            filepath TEXT,
            uid VARCHAR(255),
            size BIGINT,
            file_hash VARCHAR(255),
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP,
            in_trash BOOLEAN DEFAULT FALSE
        )
    """)
    
    # Shares table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            id SERIAL PRIMARY KEY,
            share_token VARCHAR(255) UNIQUE,
            filename VARCHAR(255),
            owner_uid VARCHAR(255),
            created_at TIMESTAMP,
            expires_at TIMESTAMP,
            access_count INTEGER DEFAULT 0
        )
    """)
    
    # ============================================
    # DETECTION TABLES
    # ============================================
    
    # Table 1: Daily anomaly results
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_anomalies (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            isolation_forest_score FLOAT,
            baseline_score FLOAT,
            flagged_by_isolation BOOLEAN DEFAULT FALSE,
            flagged_by_baseline BOOLEAN DEFAULT FALSE,
            attack_type VARCHAR(50),
            top_contributors TEXT,
            num_flagged_features INTEGER,
            confidence VARCHAR(20),
            analyst_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, user_id)
        )
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_daily_anomalies_date_user 
        ON daily_anomalies(date, user_id)
    """)
    
    # Table 2: Real-time sliding window alerts
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rare_events_alerts (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            window_type VARCHAR(50),
            detected_at TIMESTAMP NOT NULL,
            count_value INTEGER NOT NULL,
            threshold_value INTEGER NOT NULL,
            multiplier INTEGER NOT NULL,
            details JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rare_events_detected_at 
        ON rare_events_alerts(detected_at)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rare_events_user 
        ON rare_events_alerts(user_id, detected_at)
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized with detection tables")


# ============================================
# DETECTION HELPER FUNCTIONS
# ============================================

def cleanup_old_alerts():
    """Keep only last 7 days of alerts (sliding window)"""
    conn = get_db()
    cur = conn.cursor()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    cur.execute("DELETE FROM rare_events_alerts WHERE detected_at < %s", (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def store_daily_anomaly(date, user_id, iso_score, baseline_score, 
                         flagged_iso, flagged_base, attack_type, 
                         top_contributors, num_flagged, confidence, notes):
    """Store daily analysis result"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO daily_anomalies 
        (date, user_id, isolation_forest_score, baseline_score, 
         flagged_by_isolation, flagged_by_baseline, attack_type, 
         top_contributors, num_flagged_features, confidence, analyst_notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date, user_id) DO UPDATE SET
            isolation_forest_score = EXCLUDED.isolation_forest_score,
            baseline_score = EXCLUDED.baseline_score,
            flagged_by_isolation = EXCLUDED.flagged_by_isolation,
            flagged_by_baseline = EXCLUDED.flagged_by_baseline,
            attack_type = EXCLUDED.attack_type,
            top_contributors = EXCLUDED.top_contributors,
            num_flagged_features = EXCLUDED.num_flagged_features,
            confidence = EXCLUDED.confidence,
            analyst_notes = EXCLUDED.analyst_notes
    """, (date, user_id, iso_score, baseline_score, 
          flagged_iso, flagged_base, attack_type, 
          top_contributors[:500] if top_contributors else None, 
          num_flagged, confidence, notes))
    conn.commit()
    cur.close()
    conn.close()


def get_historical_anomalies(user_id, days_back=30):
    """Get past anomalies from DB - NO RECALCULATION"""
    conn = get_db()
    cur = conn.cursor()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    cur.execute("""
        SELECT * FROM daily_anomalies 
        WHERE user_id = %s AND created_at >= %s
        ORDER BY date DESC
    """, (user_id, cutoff))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "date": row['date'].isoformat(),
            "flagged_by_isolation": row['flagged_by_isolation'],
            "flagged_by_baseline": row['flagged_by_baseline'],
            "attack_type": row['attack_type'],
            "confidence": row['confidence'],
            "baseline_score": float(row['baseline_score']) if row['baseline_score'] else 0,
            "isolation_forest_score": float(row['isolation_forest_score']) if row['isolation_forest_score'] else 0,
            "analyst_notes": row['analyst_notes'],
            "top_contributors": row['top_contributors']
        })
    return result


def get_yesterdays_anomaly(user_id):
    """Get yesterday's result - if not in table, it was clean"""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM daily_anomalies 
        WHERE user_id = %s AND date = %s
    """, (user_id, yesterday))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        # Not in table means no anomaly was detected
        return {
            "date": yesterday.isoformat(),
            "user_id": user_id,
            "analyzed": True,
            "flagged": False,
            "attack_type": "NONE",
            "confidence": "HIGH",
            "baseline_score": 0,
            "analyst_notes": "No anomalies detected - day was clean"
        }
    
    return {
        "date": row['date'].isoformat(),
        "user_id": row['user_id'],
        "analyzed": True,
        "flagged": True,
        "flagged_by_isolation": row['flagged_by_isolation'],
        "flagged_by_baseline": row['flagged_by_baseline'],
        "attack_type": row['attack_type'],
        "confidence": row['confidence'],
        "baseline_score": float(row['baseline_score']) if row['baseline_score'] else 0,
        "isolation_forest_score": float(row['isolation_forest_score']) if row['isolation_forest_score'] else 0,
        "analyst_notes": row['analyst_notes']
    }


def store_real_time_alert(user_id, event_type, window_type, detected_at, 
                           count_value, threshold_value, multiplier, details=None):
    """Store real-time sliding window alert"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO rare_events_alerts 
        (user_id, event_type, window_type, detected_at, 
         count_value, threshold_value, multiplier, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, event_type, window_type, detected_at,
          count_value, threshold_value, multiplier, 
          json.dumps(details) if details else None))
    conn.commit()
    cur.close()
    conn.close()


def get_recent_alerts(user_id=None, hours=24):
    """Get recent real-time alerts"""
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