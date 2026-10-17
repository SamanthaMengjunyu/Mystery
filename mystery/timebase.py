"""Explicit civil-time resolution shared by chart and casting modules."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BEIJING_STANDARD = timezone(timedelta(hours=8))


def load_zone(tz_name):
    """Require an explicit IANA key; never fall back to the host timezone."""
    if not isinstance(tz_name, str) or not tz_name:
        raise ValueError("tz_name must be a nonempty IANA timezone name")
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"unknown or unavailable timezone: {tz_name}") from error


def wall_datetime(year, month, day, hour=0, minute=0, second=0):
    """Build a civil datetime without treating booleans as calendar numbers."""
    values = (year, month, day, hour, minute, second)
    if any(type(value) is not int for value in values):
        raise ValueError("calendar fields must be integers")
    return datetime(*values)


def validate_aware(value):
    """Reject naive or imaginary aware datetimes, including attached ZoneInfo."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("expected an aware datetime")
    back = value.astimezone(timezone.utc).astimezone(value.tzinfo)
    if (back.replace(tzinfo=None) != value.replace(tzinfo=None)
            or back.utcoffset() != value.utcoffset()):
        raise ValueError("nonexistent aware local time")
    return value


def resolve_local(value, tz_name="Asia/Shanghai", *, fold=None):
    """Resolve a naive civil time, rejecting DST gaps and unresolved overlaps.

    fold=0/1 chooses the earlier/later occurrence of a repeated clock time.
    Round trips also reject nonexistent clock times even if fold is supplied.
    """
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValueError("expected a naive local datetime")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValueError("fold must be None, 0 or 1")
    zone = load_zone(tz_name)
    candidates = {}
    for index in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=index)
        utc = candidate.astimezone(timezone.utc)
        back = utc.astimezone(zone)
        if back.replace(tzinfo=None) == value and back.fold == index:
            candidates[index] = candidate
    if not candidates:
        raise ValueError(f"nonexistent local time in {tz_name}")
    if len(candidates) > 1 and fold is None:
        raise ValueError(f"ambiguous local time in {tz_name}; specify fold=0 or fold=1")
    if fold is not None and fold not in candidates:
        raise ValueError("fold=1 is only valid for the second occurrence of an overlap")
    return candidates[fold] if fold is not None else next(iter(candidates.values()))


def time_record(local, *, basis):
    """JSON-compatible record; calculation basis is distinct from input zone."""
    validate_aware(local)
    if not isinstance(basis, str) or not basis:
        raise ValueError("calculation basis must be a nonempty string")
    return {"schema": "time-v1", "local": local.isoformat(),
            "utc": local.astimezone(timezone.utc).isoformat(),
            "timezone": getattr(local.tzinfo, "key", str(local.tzinfo)),
            "fold": local.fold, "basis": basis}


def beijing_clock(local):
    """Naive UTC+08 standard clock, with historical DST removed."""
    validate_aware(local)
    return local.astimezone(BEIJING_STANDARD).replace(tzinfo=None)
