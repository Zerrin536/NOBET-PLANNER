from typing import Dict, Set, Tuple

from src.unavailability_repo import list_unavailability

def build_blocked_days() -> Dict[int, Set[str]]:
    """
    Eski uyumluluk: sadece 'bu gün çalışamaz' set'i.
    """
    blocked_any, _ = build_blocked_days_with_type()
    return blocked_any

def build_blocked_days_with_type() -> Tuple[Dict[int, Set[str]], Dict[int, Dict[str, str]]]:
    """
    Yeni: hem set (hızlı kontrol) hem de tip bilgisi.
    returns:
      blocked_any: {staff_id: set(YYYY-MM-DD)}
      blocked_type: {staff_id: {YYYY-MM-DD: "rapor"|"yillik_izin"}}
    """
    rows = list_unavailability(None)  # hepsi
    blocked_any: Dict[int, Set[str]] = {}
    blocked_type: Dict[int, Dict[str, str]] = {}

    for r in rows:
        sid = int(r["staff_id"])
        d = str(r["date"])
        t = str(r["type"])  # "rapor" | "yillik_izin"

        blocked_any.setdefault(sid, set()).add(d)
        blocked_type.setdefault(sid, {})[d] = t

    return blocked_any, blocked_type
