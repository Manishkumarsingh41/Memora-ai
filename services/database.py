import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from config import get_settings

settings = get_settings()

def _get_conn():
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                drive_file_id TEXT NOT NULL,
                folder TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

def save_file_metadata(user_id: str, file_name: str, file_type: str, drive_file_id: str, folder: str) -> int:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO files (user_id, file_name, file_type, drive_file_id, folder, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, file_name, file_type, drive_file_id, folder, now),
        )
        return cursor.lastrowid

def list_files(user_id: str) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]

def find_files_by_name(user_id: str, query: str) -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE user_id = ? AND LOWER(file_name) LIKE ?",
            (user_id, f"%{query.lower()}%"),
        ).fetchall()
    return [dict(row) for row in rows]

def get_file_by_id(file_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
    return dict(row) if row else None
