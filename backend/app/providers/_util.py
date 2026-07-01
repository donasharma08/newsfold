from datetime import datetime, timezone
import math


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.replace("Z", "+00:00")
    for fmt in (None,):  # try fromisoformat first
        try:
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def minutes_ago(dt: datetime | None) -> int:
    if not dt:
        return 0
    delta = datetime.now(timezone.utc) - dt
    return max(0, int(delta.total_seconds() // 60))


def read_estimate(text: str) -> int:
    words = len((text or "").split())
    return max(2, math.ceil(words / 200)) if words else 4


def scope_of(country_param: str | None, national_country: str) -> str:
    """If we queried with the national country, label national; else world."""
    if country_param and country_param.lower() == national_country.lower():
        return "national"
    return "international"
