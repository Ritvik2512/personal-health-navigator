import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "health_navigator.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                patient_context TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.commit()


def load_session(session_id: str) -> dict:
    with get_connection() as conn:
        session = conn.execute(
            "SELECT patient_context FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        if not session:
            return {"patient_context": {}, "history": []}

        messages = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        ).fetchall()

        return {
            "patient_context": json.loads(session["patient_context"]),
            "history": [{"role": m["role"], "content": m["content"]} for m in messages],
        }


def save_session(session_id: str, patient_context: dict, new_messages: list):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE sessions SET patient_context = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps(patient_context), now, session_id)
            )
        else:
            conn.execute(
                "INSERT INTO sessions (session_id, patient_context, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, json.dumps(patient_context), now, now)
            )

        for msg in new_messages:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, msg["role"], msg["content"], now)
            )

        conn.commit()
