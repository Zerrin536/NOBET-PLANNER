from typing import Dict, Set, Tuple
from src.unavailability_repo import list_unavailability
from src.requests_repo import list_approved_requests

def build_blocked_days_with_type(
    year: int | None,
    month: int | None
) -> Tuple[Dict[int, Set[str]], Dict[int, Dict[str, str]], Dict[int, Set[str]]]:
    """
    returns:
      blocked_any: {staff_id: set(YYYY-MM-DD)}  -> rapor/izin + approved HARD istek
      blocked_type: {staff_id: {YYYY-MM-DD: type}} -> rapor/yillik_izin/onayli_istek_hard
      soft_avoid: {staff_id: set(YYYY-MM-DD)} -> approved SOFT istek (mümkünse boş)
    """
    rows = list_unavailability(None)
    blocked_any: Dict[int, Set[str]] = {}
    blocked_type: Dict[int, Dict[str, str]] = {}
    soft_avoid: Dict[int, Set[str]] = {}

    # rapor / yıllık izin (hard)
    for r in rows:
        sid = int(r["staff_id"])
        d = str(r["date"])
        t = str(r["type"])  # rapor | yillik_izin
        blocked_any.setdefault(sid, set()).add(d)
        blocked_type.setdefault(sid, {})[d] = t

    # onaylı istekler
    if year is not None and month is not None:
        reqs = list_approved_requests(year, month)
        for r in reqs:
            sid = int(r["staff_id"])
            d = str(r["date"])
            kind = (r.get("request_kind") or "HARD").upper()

            if kind == "HARD":
                blocked_any.setdefault(sid, set()).add(d)
                blocked_type.setdefault(sid, {})[d] = "onayli_istek_hard"
            else:
                soft_avoid.setdefault(sid, set()).add(d)

    return blocked_any, blocked_type, soft_avoid
