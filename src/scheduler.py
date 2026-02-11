from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple, Set, Optional

from src.calendar_utils import iter_month_days

ShiftType = str  # 'DAY' | 'NIGHT' | 'D24' | 'RAPOR' | 'YILLIK_IZIN'

@dataclass(frozen=True)
class Shift:
    day: str
    shift_type: ShiftType

SHIFT_HOURS = {"DAY": 8, "NIGHT": 16, "D24": 24}

def build_required_shifts(year: int, month: int) -> List[Shift]:
    shifts: List[Shift] = []
    days = iter_month_days(year, month)
    for d in days:
        if d.is_weekend:
            for _ in range(12):
                shifts.append(Shift(d.iso, "D24"))
        else:
            for _ in range(12):
                shifts.append(Shift(d.iso, "DAY"))
            for _ in range(12):
                shifts.append(Shift(d.iso, "NIGHT"))
    return shifts

def _prev_day_iso(day_iso: str) -> str:
    return (date.fromisoformat(day_iso) - timedelta(days=1)).isoformat()

def _is_weekend(day_iso: str) -> bool:
    return date.fromisoformat(day_iso).weekday() >= 5

def _day_kind(day_iso: str) -> str:
    return "WEEKEND" if _is_weekend(day_iso) else "WEEKDAY"

def _get_prev_shift_type(
    staff_id: int,
    day_iso: str,
    assigned_by_day: Dict[str, List[Tuple[int, ShiftType]]],
    blocked_type: Optional[Dict[int, Dict[str, str]]] = None,
) -> ShiftType | None:
    prev = _prev_day_iso(day_iso)

    # Dün rapor/izin miydi?
    if blocked_type is not None:
        t = blocked_type.get(staff_id, {}).get(prev)
        if t == "rapor":
            return "RAPOR"
        if t == "yillik_izin":
            return "YILLIK_IZIN"

    # Dün vardiya aldı mı?
    for sid, stype in assigned_by_day.get(prev, []):
        if sid == staff_id:
            return stype
    return None

def _match(rule_val: str, actual: str) -> bool:
    return rule_val == "ANY" or rule_val == actual

def _match_day(rule_day: str, cur_day_iso: str) -> bool:
    if rule_day == "ANY":
        return True
    return rule_day == _day_kind(cur_day_iso)

def _violates_transition_rules(prev: ShiftType | None, cur: ShiftType, cur_day_iso: str, transition_rules: List[Dict]) -> bool:
    if prev is None:
        return False

    for r in transition_rules:
        apply_day = r.get("apply_day", "ANY")
        if not _match_day(apply_day, cur_day_iso):
            continue
        if _match(r["prev_type"], prev) and _match(r["next_type"], cur):
            return True

    return False

def can_assign(
    staff_id: int,
    shift: Shift,
    assigned_by_day: Dict[str, List[Tuple[int, ShiftType]]],
    blocked_any: Dict[int, Set[str]],
    transition_rules: List[Dict] | None = None,
    blocked_type: Optional[Dict[int, Dict[str, str]]] = None,
) -> bool:
    transition_rules = transition_rules or []
    day = shift.day
    stype = shift.shift_type

    # Hard block
    if day in blocked_any.get(staff_id, set()):
        return False

    # aynı gün çift vardiya yok
    for sid, _s in assigned_by_day.get(day, []):
        if sid == staff_id:
            return False

    prev = _get_prev_shift_type(staff_id, day, assigned_by_day, blocked_type=blocked_type)

    if _violates_transition_rules(prev, stype, day, transition_rules):
        return False

    return True

def _build_assigned_by_day(assignments: List[Tuple[str, ShiftType, int]]) -> Dict[str, List[Tuple[int, ShiftType]]]:
    out: Dict[str, List[Tuple[int, ShiftType]]] = {}
    for d, stype, sid in assignments:
        out.setdefault(d, []).append((sid, stype))
    return out

def _compute_hours(assignments: List[Tuple[str, ShiftType, int]], staff_ids: List[int]) -> Dict[int, int]:
    hours = {sid: 0 for sid in staff_ids}
    for _d, stype, sid in assignments:
        hours[sid] += SHIFT_HOURS.get(stype, 0)
    return hours

def generate_schedule(
    year: int,
    month: int,
    staff_ids: List[int],
    blocked_any: Dict[int, Set[str]],
    transition_rules: List[Dict] | None = None,
    blocked_type: Optional[Dict[int, Dict[str, str]]] = None,
    soft_avoid: Optional[Dict[int, Set[str]]] = None,
) -> Tuple[List[Tuple[str, ShiftType, int]], List[Shift]]:
    required = build_required_shifts(year, month)
    counts = {sid: 0 for sid in staff_ids}
    assigned_by_day: Dict[str, List[Tuple[int, ShiftType]]] = {}
    soft_avoid = soft_avoid or {}

    assignments: List[Tuple[str, ShiftType, int]] = []
    unfilled: List[Shift] = []

    for sh in required:
        def score(sid: int):
            penalty = 1 if sh.day in soft_avoid.get(sid, set()) else 0
            return (penalty, counts.get(sid, 0))

        candidates = sorted(staff_ids, key=score)

        picked = None
        for sid in candidates:
            if can_assign(
                sid, sh, assigned_by_day, blocked_any,
                transition_rules=transition_rules,
                blocked_type=blocked_type
            ):
                picked = sid
                break

        if picked is None:
            unfilled.append(sh)
            continue

        assignments.append((sh.day, sh.shift_type, picked))
        counts[picked] += 1
        assigned_by_day.setdefault(sh.day, []).append((picked, sh.shift_type))

    return assignments, unfilled

def repair_to_meet_min_hours(
    year: int,
    month: int,
    assignments: List[Tuple[str, ShiftType, int]],
    staff_ids: List[int],
    blocked_any: Dict[int, Set[str]],
    min_required_hours: int,
    transition_rules: List[Dict] | None = None,
    blocked_type: Optional[Dict[int, Dict[str, str]]] = None,
    max_iters: int = 20000,
) -> Tuple[List[Tuple[str, ShiftType, int]], Dict[int, int], int]:
    transition_rules = transition_rules or []
    assigned_by_day = _build_assigned_by_day(assignments)
    hours = _compute_hours(assignments, staff_ids)

    def deficits():
        return [sid for sid in staff_ids if hours[sid] < min_required_hours]

    def surpluses():
        return [sid for sid in staff_ids if hours[sid] > min_required_hours]

    swaps = 0
    it = 0

    while True:
        it += 1
        if it > max_iters:
            break

        deficit_list = sorted(deficits(), key=lambda s: hours[s])
        if not deficit_list:
            break

        surplus_list = sorted(surpluses(), key=lambda s: hours[s], reverse=True)
        if not surplus_list:
            break

        d_staff = deficit_list[0]
        moved = False

        for idx, (d, stype, s_staff) in enumerate(assignments):
            if s_staff not in surplus_list:
                continue

            sh = Shift(d, stype)
            if not can_assign(
                d_staff, sh, assigned_by_day, blocked_any,
                transition_rules=transition_rules,
                blocked_type=blocked_type
            ):
                continue

            h = SHIFT_HOURS.get(stype, 0)
            if hours[s_staff] - h < min_required_hours:
                continue

            day_list = assigned_by_day.get(d, [])
            removed = False
            for j in range(len(day_list)):
                if day_list[j][0] == s_staff and day_list[j][1] == stype:
                    day_list.pop(j)
                    removed = True
                    break
            if not removed:
                continue

            day_list.append((d_staff, stype))
            assigned_by_day[d] = day_list

            assignments[idx] = (d, stype, d_staff)
            hours[s_staff] -= h
            hours[d_staff] += h

            swaps += 1
            moved = True
            break

        if not moved:
            break

    return assignments, hours, swaps

def generate_schedule_hard_min_hours(
    year: int,
    month: int,
    staff_ids: List[int],
    blocked_any: Dict[int, Set[str]],
    min_required_hours: int,
    transition_rules: List[Dict] | None = None,
    blocked_type: Optional[Dict[int, Dict[str, str]]] = None,
    soft_avoid: Optional[Dict[int, Set[str]]] = None,
) -> Tuple[List[Tuple[str, ShiftType, int]], List[Shift], Dict[int, int], int]:
    assignments, unfilled = generate_schedule(
        year, month, staff_ids, blocked_any,
        transition_rules=transition_rules,
        blocked_type=blocked_type,
        soft_avoid=soft_avoid
    )
    assignments, hours, swaps = repair_to_meet_min_hours(
        year, month, assignments, staff_ids, blocked_any, min_required_hours,
        transition_rules=transition_rules,
        blocked_type=blocked_type
    )
    return assignments, unfilled, hours, swaps
