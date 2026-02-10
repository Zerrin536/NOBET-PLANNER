from typing import Optional
from datetime import datetime
from src.db import get_conn

def add_request(staff_id: int, day: str, note: str) -> None:
    note = (note or "").strip()
    if not note:
        return
    created_at = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO requests (staff_id, date, note, created_at, status) VALUES (?, ?, ?, ?, 'pending')",
            (staff_id, day, note, created_at),
        )
        conn.commit()

def list_requests(status: Optional[str] = None):
    q = """
    SELECT r.id, r.staff_id, s.full_name, r.date, r.note, r.created_at, r.status
    FROM requests r
    JOIN staff s ON s.id = r.staff_id
    """
    params = []
    if status:
        q += " WHERE r.status = ?"
        params.append(status)
    q += " ORDER BY r.date ASC, r.created_at DESC"
    with get_conn() as conn:
        return conn.execute(q, params).fetchall()

def set_request_status(req_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE requests SET status = ? WHERE id = ?", (status, req_id))
        conn.commit()

def delete_request(req_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM requests WHERE id = ?", (req_id,))
        conn.commit()
