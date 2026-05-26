from models.database import get_db
from datetime import datetime, timezone

class FileModel:
    @staticmethod
    def track_file(filename: str, filepath: str, uid: str, size: int, file_hash: str):
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO files (filename, filepath, uid, size, file_hash, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (filename, uid) DO UPDATE
            SET updated_at = %s, size = %s, file_hash = %s, version = files.version + 1
        """, (filename, filepath, uid, size, file_hash, datetime.now(timezone.utc), 
              datetime.now(timezone.utc), datetime.now(timezone.utc), size, file_hash))
        
        conn.commit()
        cur.close()
        conn.close()
    
    @staticmethod
    def mark_deleted(filename: str, uid: str, permanent: bool = False):
        conn = get_db()
        cur = conn.cursor()
        
        if permanent:
            cur.execute("DELETE FROM files WHERE filename = %s AND uid = %s", (filename, uid))
        else:
            cur.execute("""
                UPDATE files SET deleted_at = %s, in_trash = TRUE 
                WHERE filename = %s AND uid = %s
            """, (datetime.now(timezone.utc), filename, uid))
        
        conn.commit()
        cur.close()
        conn.close()