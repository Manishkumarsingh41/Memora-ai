from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from config import get_settings
from services import rag
from logging_config import get_logger
import sqlite3

settings = get_settings()
logger = get_logger("admin")
router = APIRouter(prefix="", tags=["admin"], include_in_schema=False)

def _verify_admin(request: Request):
    if request.headers.get("X-Admin-Secret") != settings.admin_secret:
        raise HTTPException(status_code=401)

@router.get("/users")
async def list_users(request: Request):
    _verify_admin(request)
    try:
        conn = sqlite3.connect(settings.sqlite_db_path)
        users = conn.execute("SELECT DISTINCT user_id FROM files").fetchall()
        conn.close()
        return {"status": "ok", "users": [u[0] for u in users]}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500)

@router.get("/stats")
async def stats(request: Request):
    _verify_admin(request)
    try:
        conn = sqlite3.connect(settings.sqlite_db_path)
        users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM files").fetchone()[0]
        files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        memory_entries = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        conn.close()
        return {"status": "ok", "users": users, "files": files, "memory": memory_entries}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500)

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    _verify_admin(request)
    try:
        conn = sqlite3.connect(settings.sqlite_db_path)
        conn.execute("DELETE FROM files WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        rag.delete_user_all_docs(user_id)
        return {"status": "ok", "message": f"User {user_id} deleted"}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500)
