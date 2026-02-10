from typing import List, Optional
from src.db import get_conn

def add_staff(full_name: str) -> None:
    name = full_name.strip()
    if not name:
        return
    with get_conn() as conn:
        conn.execute("INSERT INTO staff (full_name, is_active) VALUES (?, 1)", (name,))
        conn.commit()

def add_staff_bulk(names: List[str]) -> int:
    cleaned = [n.strip() for n in names if n.strip()]
    if not cleaned:
        return 0
    with get_conn() as conn:
        conn.executemany("INSERT INTO staff (full_name, is_active) VALUES (?, 1)", [(n,) for n in cleaned])
        conn.commit()
    return len(cleaned)

def list_staff(only_active: Optional[bool] = None):
    q = "SELECT id, full_name, is_active FROM staff"
    params = []
    if only_active is True:
        q += " WHERE is_active = 1"
    elif only_active is False:
        q += " WHERE is_active = 0"
    q += " ORDER BY full_name COLLATE NOCASE"
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
    return rows

def set_staff_active(staff_id: int, is_active: bool) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE staff SET is_active = ? WHERE id = ?", (1 if is_active else 0, staff_id))
        conn.commit()

def delete_staff(staff_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
        conn.commit()
