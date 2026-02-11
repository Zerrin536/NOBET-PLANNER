from typing import List
from src.db import get_conn

def add_holiday(day: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO holidays (date) VALUES (?)", (day,))
        conn.commit()

def add_holidays(days: List[str]) -> int:
    if not days:
        return 0
    rows = [(d,) for d in days]
    with get_conn() as conn:
        conn.executemany("INSERT OR IGNORE INTO holidays (date) VALUES (?)", rows)
        conn.commit()
    return len(days)

def list_holidays() -> List[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT date FROM holidays ORDER BY date ASC").fetchall()
    return [r["date"] for r in rows]

def delete_holiday(day: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM holidays WHERE date = ?", (day,))
        conn.commit()
