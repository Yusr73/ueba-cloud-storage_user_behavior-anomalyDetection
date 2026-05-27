import psycopg2
import psycopg2.extras
from config import Config

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
    
    conn.commit()
    cur.close()
    conn.close()