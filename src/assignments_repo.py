from typing import List, Tuple, Optional
from src.db import get_conn

def clear_month(year: int, month: int) -> None:
    prefix = f"{year:04d}-{month:02d}-"
    with get_conn() as conn:
        conn.execute("DELETE FROM assignments WHERE date LIKE ?", (prefix + "%",))
        conn.commit()

def insert_assignments(rows: List[Tuple[str, str, int]]) -> None:
    if not rows:
        return
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO assignments (date, shift_type, staff_id) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()

def list_month(year: int, month: int):
    prefix = f"{year:04d}-{month:02d}-"
    q = """
    SELECT a.date, a.shift_type, a.staff_id, s.full_name
    FROM assignments a
    JOIN staff s ON s.id = a.staff_id
    WHERE a.date LIKE ?
    ORDER BY a.date ASC, a.shift_type ASC, s.full_name COLLATE NOCASE ASC
    """
    with get_conn() as conn:
        return conn.execute(q, (prefix + "%",)).fetchall()
