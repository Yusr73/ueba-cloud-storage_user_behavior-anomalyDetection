import hashlib
from models.database import get_db
from utils.security import hash_password, verify_password
from datetime import datetime, timezone

class UserModel:
    @staticmethod
    def create_user(username: str, password: str, email: str = None):
        conn = get_db()
        cur = conn.cursor()
        
        uid = f"{username}-{hashlib.md5(username.encode()).hexdigest()[:8]}"
        hashed = hash_password(password)
        
        cur.execute("""
            INSERT INTO users (uid, username, email, hashed_password, role, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING uid
        """, (uid, username, email, hashed, 'user', datetime.now(timezone.utc)))
        
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return result['uid'] if result else None
    
    @staticmethod
    def authenticate(username: str, password: str):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT uid, username, hashed_password, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and verify_password(password, user['hashed_password']):
            return {"uid": user['uid'], "username": user['username'], "role": user['role']}
        return None
    
    @staticmethod
    def get_user_by_uid(uid: str):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT uid, username, role, email FROM users WHERE uid = %s", (uid,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user