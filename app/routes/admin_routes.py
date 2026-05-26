from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models.database import get_db
from controllers.auth_controller import get_current_user
import json
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

def require_admin(current_user = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/database", response_class=HTMLResponse)
async def database_viewer(request: Request, current_user = Depends(require_admin)):
    return templates.TemplateResponse("admin_database.html", {"request": request})

@router.get("/api/stats")
async def get_stats(current_user = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    
    stats = {}
    
    tables = ['users', 'logs', 'files', 'shares']
    for table in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            stats[table] = cur.fetchone()[0]
        except:
            stats[table] = 0
    
    # Recent activity
    try:
        cur.execute("""
            SELECT type, COUNT(*) as count 
            FROM logs 
            WHERE time > NOW() - INTERVAL '24 hours'
            GROUP BY type 
            ORDER BY count DESC 
            LIMIT 10
        """)
        recent_activity = [{"type": row[0], "count": row[1]} for row in cur.fetchall()]
    except:
        recent_activity = []
    
    cur.close()
    conn.close()
    
    return {"counts": stats, "recent_activity": recent_activity}

@router.get("/api/tables")
async def get_tables(current_user = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return {"tables": tables}

@router.get("/api/table/{table_name}")
async def get_table_data(table_name: str, current_user = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    
    # Get column names
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    columns = [{"name": row[0], "type": row[1]} for row in cur.fetchall()]
    
    # Get data
    try:
        cur.execute(f'SELECT * FROM "{table_name}" ORDER BY id DESC LIMIT 500')
        rows = cur.fetchall()
    except:
        rows = []
    
    # Convert rows to list of dicts
    data = []
    for row in rows:
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, dict):
                value = json.dumps(value)
            row_dict[col["name"]] = str(value) if value else ""
        data.append(row_dict)
    
    cur.close()
    conn.close()
    
    return {"columns": columns, "data": data, "count": len(data)}

@router.delete("/api/table/{table_name}/{record_id}")
async def delete_record(table_name: str, record_id: int, current_user = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute(f'DELETE FROM "{table_name}" WHERE id = %s', (record_id,))
        conn.commit()
        success = True
        error = None
    except Exception as e:
        success = False
        error = str(e)
    
    cur.close()
    conn.close()
    
    if success:
        return {"success": True}
    else:
        return {"success": False, "error": error}