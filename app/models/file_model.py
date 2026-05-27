from models.database import get_db
from datetime import datetime, timezone

class FileModel:
    @staticmethod
    def track_file(filename: str, filepath: str, uid: str, size: int, file_hash: str):
        conn = get_db()
        cur = conn.cursor()
        
        # D'abord, vérifier si le fichier existe déjà
        cur.execute("""
            SELECT id FROM files WHERE filename = %s AND uid = %s
        """, (filename, uid))
        
        existing = cur.fetchone()
        
        if existing:
            # Mettre à jour
            cur.execute("""
                UPDATE files 
                SET filepath = %s, size = %s, file_hash = %s, 
                    updated_at = %s, version = version + 1
                WHERE filename = %s AND uid = %s
            """, (filepath, size, file_hash, datetime.now(timezone.utc), filename, uid))
        else:
            # Insérer nouveau
            cur.execute("""
                INSERT INTO files (filename, filepath, uid, size, file_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (filename, filepath, uid, size, file_hash, datetime.now(timezone.utc), datetime.now(timezone.utc)))
        
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