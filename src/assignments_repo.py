import sqlite3
from typing import List, Dict

def _connect():
    try:
        from src.db import get_conn  # type: ignore
        return get_conn()
    except Exception:
        return sqlite3.connect("nobet_planner.sqlite3", check_same_thread=False)

def ensure_assignments_table():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,        -- YYYY-MM-DD
            shift_type TEXT NOT NULL,  -- DAY/NIGHT/D24
            staff_id INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn

def clear_month(year: int, month: int):
    from datetime import date
    start = date(year, month, 1).isoformat()
    if month == 12:
        end = date(year + 1, 1, 1).isoformat()
    else:
        end = date(year, month + 1, 1).isoformat()

    conn = ensure_assignments_table()
    cur = conn.cursor()
    cur.execute("DELETE FROM assignments WHERE date >= ? AND date < ?", (start, end))
    conn.commit()

def insert_assignments(assignments: List[Dict]):
    """
    assignments: [{"date":"YYYY-MM-DD","shift_type":"DAY","staff_id":1}, ...]
    """
    conn = ensure_assignments_table()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO assignments(date, shift_type, staff_id) VALUES(?,?,?)",
        [(a["date"], a["shift_type"], int(a["staff_id"])) for a in assignments],
    )
    conn.commit()

def list_month(year: int, month: int) -> List[Dict]:
    """
    Return rows including staff_id + full_name so UI can compute matrices.
    """
    from datetime import date
    start = date(year, month, 1).isoformat()
    if month == 12:
        end = date(year + 1, 1, 1).isoformat()
    else:
        end = date(year, month + 1, 1).isoformat()

    conn = ensure_assignments_table()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.date, a.shift_type, a.staff_id, s.full_name
        FROM assignments a
        JOIN staff s ON s.id = a.staff_id
        WHERE a.date >= ? AND a.date < ?
        ORDER BY a.date ASC, a.shift_type ASC, s.full_name ASC
        """,
        (start, end),
    )
    return [dict(r) for r in cur.fetchall()]
