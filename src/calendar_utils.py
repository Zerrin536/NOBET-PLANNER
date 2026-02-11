from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class DayInfo:
    day: date
    iso: str
    weekday: int         # 0=Mon ... 6=Sun
    is_weekend: bool

def month_range(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end

def iter_month_days(year: int, month: int):
    start, end = month_range(year, month)
    cur = start
    out = []
    while cur < end:
        out.append(
            DayInfo(
                day=cur,
                iso=cur.isoformat(),
                weekday=cur.weekday(),
                is_weekend=(cur.weekday() >= 5),
            )
        )
        cur += timedelta(days=1)
    return out

def count_weekdays_excluding_holidays(year: int, month: int, holiday_isos: set[str]) -> int:
    days = iter_month_days(year, month)
    count = 0
    for d in days:
        if (not d.is_weekend) and (d.iso not in holiday_isos):
            count += 1
    return count
