import sqlite3
from typing import List, Dict

def _connect():
    try:
        from src.db import get_conn  # type: ignore
        return get_conn()
    except Exception:
        return sqlite3.connect("nobet_planner.sqlite3", check_same_thread=False)

def ensure_rules_table():
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prev_type TEXT NOT NULL,   -- DAY / NIGHT / D24 / ANY / RAPOR / YILLIK_IZIN
            next_type TEXT NOT NULL,   -- DAY / NIGHT / D24 / ANY
            is_active INTEGER NOT NULL DEFAULT 1,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # --- Migration: apply_day kolonunu yoksa ekle ---
    cur.execute("PRAGMA table_info(rules)")
    cols = {row["name"] for row in cur.fetchall()}
    if "apply_day" not in cols:
        cur.execute("ALTER TABLE rules ADD COLUMN apply_day TEXT NOT NULL DEFAULT 'ANY'")
        conn.commit()

    return conn

def add_rule(prev_type: str, next_type: str, apply_day: str = "ANY", note: str = "") -> int:
    conn = ensure_rules_table()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rules(prev_type, next_type, apply_day, is_active, note) VALUES(?,?,?,1,?)",
        (prev_type, next_type, apply_day, note or ""),
    )
    conn.commit()
    return int(cur.lastrowid)

def list_rules(active_only: bool | None = None) -> List[Dict]:
    conn = ensure_rules_table()
    cur = conn.cursor()
    if active_only is None:
        cur.execute("SELECT * FROM rules ORDER BY id DESC")
    elif active_only:
        cur.execute("SELECT * FROM rules WHERE is_active=1 ORDER BY id DESC")
    else:
        cur.execute("SELECT * FROM rules WHERE is_active=0 ORDER BY id DESC")
    rows = cur.fetchall()
    return [dict(r) for r in rows]

def set_rule_active(rule_id: int, is_active: bool):
    conn = ensure_rules_table()
    cur = conn.cursor()
    cur.execute("UPDATE rules SET is_active=? WHERE id=?", (1 if is_active else 0, rule_id))
    conn.commit()

def delete_rule(rule_id: int):
    conn = ensure_rules_table()
    cur = conn.cursor()
    cur.execute("DELETE FROM rules WHERE id=?", (rule_id,))
    conn.commit()
