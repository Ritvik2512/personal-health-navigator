import sqlite3
import json
import os
from datetime import datetime, date

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                created_at TEXT
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


def log_usage(session_id: str, input_tokens: int, output_tokens: int):
    cost = (input_tokens * 0.00000025) + (output_tokens * 0.00000125)
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO api_usage (session_id, input_tokens, output_tokens, cost, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, input_tokens, output_tokens, cost, now)
        )
        conn.commit()
    return cost


def get_daily_usage() -> dict:
    today = date.today().isoformat()
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_requests,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(cost), 0) as estimated_cost_usd
            FROM api_usage
            WHERE 1=1
        """).fetchone()

    cost = row["estimated_cost_usd"]
    budget = 5.0

    return {
        "date": today,
        "total_requests": row["total_requests"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "estimated_cost_usd": round(cost, 4),
        "budget_remaining_usd": round(budget - cost, 4),
    }


def get_daily_cost() -> float:
    return get_daily_usage()["estimated_cost_usd"]