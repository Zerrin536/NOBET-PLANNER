from typing import List, Optional
from datetime import date
from src.db import get_conn

def add_unavailability(staff_id: int, day: str, utype: str, note: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO unavailability (staff_id, date, type, note) VALUES (?, ?, ?, ?)",
            (staff_id, day, utype, note.strip() if note else None),
        )
        conn.commit()

def add_unavailability_range(staff_id: int, days: List[str], utype: str, note: str = "") -> int:
    rows = [(staff_id, d, utype, note.strip() if note else None) for d in days]
    if not rows:
        return 0
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO unavailability (staff_id, date, type, note) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    return len(rows)

def list_unavailability(staff_id: Optional[int] = None):
    q = """
    SELECT u.id, u.staff_id, s.full_name, u.date, u.type, COALESCE(u.note,'') AS note
    FROM unavailability u
    JOIN staff s ON s.id = u.staff_id
    """
    params = []
    if staff_id is not None:
        q += " WHERE u.staff_id = ?"
        params.append(staff_id)
    q += " ORDER BY u.date ASC, s.full_name COLLATE NOCASE ASC"
    with get_conn() as conn:
        return conn.execute(q, params).fetchall()

def delete_unavailability(row_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM unavailability WHERE id = ?", (row_id,))
        conn.commit()
