import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "nobet_planner.sqlite3"

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS unavailability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            note TEXT,
            UNIQUE(staff_id, date, type),
            FOREIGN KEY (staff_id) REFERENCES staff(id)
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (staff_id) REFERENCES staff(id)
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS holidays (
            date TEXT PRIMARY KEY
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            shift_type TEXT NOT NULL,
            staff_id INTEGER NOT NULL,
            UNIQUE(date, shift_type, staff_id),
            FOREIGN KEY (staff_id) REFERENCES staff(id)
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)

        conn.commit()
