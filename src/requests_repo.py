import sqlite3
from typing import List, Dict, Optional

def _connect():
    try:
        from src.db import get_conn  # type: ignore
        return get_conn()
    except Exception:
        return sqlite3.connect("nobet_planner.sqlite3", check_same_thread=False)

def ensure_requests_table():
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # created_at için DEFAULT eklemiyoruz çünkü sende tablo zaten var ve migration zor.
    # Biz INSERT ederken created_at'i daima kendimiz set edeceğiz.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            date TEXT NOT NULL,            -- YYYY-MM-DD
            note TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', -- pending/approved/rejected
            created_at TEXT NOT NULL,
            request_kind TEXT NOT NULL DEFAULT 'HARD'
        )
    """)
    conn.commit()

    # Migration: request_kind yoksa ekle (HARD/SOFT)
    cur.execute("PRAGMA table_info(requests)")
    cols = {row["name"] for row in cur.fetchall()}
    if "request_kind" not in cols:
        cur.execute("ALTER TABLE requests ADD COLUMN request_kind TEXT NOT NULL DEFAULT 'HARD'")
        conn.commit()

    return conn

def add_request(staff_id: int, day_iso: str, note: str, request_kind: str = "HARD") -> int:
    conn = ensure_requests_table()
    cur = conn.cursor()

    # created_at NOT NULL hatasını kesin çözmek için created_at'i her zaman yazıyoruz:
    cur.execute(
        "INSERT INTO requests(staff_id, date, note, status, request_kind, created_at) "
        "VALUES(?,?,?,?,?, datetime('now'))",
        (staff_id, day_iso, note, "pending", request_kind),
    )
    conn.commit()
    return int(cur.lastrowid)

def list_requests(status: Optional[str] = None) -> List[Dict]:
    conn = ensure_requests_table()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if status is None:
        cur.execute("""
            SELECT r.*, s.full_name
            FROM requests r
            JOIN staff s ON s.id = r.staff_id
            ORDER BY r.date DESC, r.id DESC
        """)
    else:
        cur.execute("""
            SELECT r.*, s.full_name
            FROM requests r
            JOIN staff s ON s.id = r.staff_id
            WHERE r.status=?
            ORDER BY r.date DESC, r.id DESC
        """, (status,))
    return [dict(x) for x in cur.fetchall()]

def set_request_status(request_id: int, status: str):
    conn = ensure_requests_table()
    cur = conn.cursor()
    cur.execute("UPDATE requests SET status=? WHERE id=?", (status, request_id))
    conn.commit()

def delete_request(request_id: int):
    conn = ensure_requests_table()
    cur = conn.cursor()
    cur.execute("DELETE FROM requests WHERE id=?", (request_id,))
    conn.commit()

def list_approved_requests(year: int, month: int) -> List[Dict]:
    from datetime import date
    start = date(year, month, 1).isoformat()
    if month == 12:
        end = date(year + 1, 1, 1).isoformat()
    else:
        end = date(year, month + 1, 1).isoformat()

    conn = ensure_requests_table()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id, r.staff_id, r.date, r.note, r.status, r.created_at, r.request_kind, s.full_name
        FROM requests r
        JOIN staff s ON s.id = r.staff_id
        WHERE r.status = 'approved'
          AND r.date >= ?
          AND r.date < ?
        ORDER BY r.date ASC
        """,
        (start, end),
    )
    return [dict(x) for x in cur.fetchall()]
