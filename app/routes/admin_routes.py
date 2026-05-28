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
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Page HTML - accessible à tous (la vérification se fait en JavaScript)
@router.get("/database", response_class=HTMLResponse)
async def database_viewer(request: Request):
    return templates.TemplateResponse("admin_database.html", {"request": request})

# API - protégées par le backend
@router.get("/api/stats")
async def get_stats(current_user = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    stats = {}
    for table in ['users', 'logs', 'files', 'shares']:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            row = cur.fetchone()
            stats[table] = row['count'] if row else 0
        except:
            stats[table] = 0
    cur.close()
    conn.close()
    return {"counts": stats}

@router.get("/api/table/{table_name}")
async def get_table_data(table_name: str, current_user = Depends(require_admin)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table_name,))
    columns = [{"name": row['column_name'], "type": row['data_type']} for row in cur.fetchall()]
    try:
        cur.execute(f'SELECT * FROM "{table_name}" ORDER BY id DESC LIMIT 500')
        rows = cur.fetchall()
    except:
        rows = []
    data = []
    for row in rows:
        row_dict = {}
        for col in columns:
            value = row[col['name']]
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, dict):
                value = json.dumps(value)
            row_dict[col['name']] = str(value) if value else ""
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
    return {"success": success, "error": error}