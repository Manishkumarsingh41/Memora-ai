import sqlite3
from datetime import datetime
from typing import List, Dict, Any
from config import get_settings

settings = get_settings()

def _get_conn():
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    return conn

def add_memory(user_id: str, role: str, content: str):
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO memory (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now),
        )

def get_memory(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM memory WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]

def clear_memory(user_id: str):
    with _get_conn() as conn:
        conn.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))

def get_memory_summary(user_id: str) -> Dict[str, Any]:
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM memory WHERE user_id = ?", (user_id,)).fetchone()[0]
        user_msgs = conn.execute("SELECT COUNT(*) FROM memory WHERE user_id = ? AND role = 'user'", (user_id,)).fetchone()[0]
        asst_msgs = conn.execute("SELECT COUNT(*) FROM memory WHERE user_id = ? AND role = 'assistant'", (user_id,)).fetchone()[0]
    
    return {
        "total_messages": total,
        "user_messages": user_msgs,
        "assistant_messages": asst_msgs,
    }
