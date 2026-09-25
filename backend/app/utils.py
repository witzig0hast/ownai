from datetime import datetime, timezone


def parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ensure_utc(parsed)


def ensure_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True) columns; Postgres (asyncpg) does not.
    Normalize so comparisons against timezone-aware `datetime.now(timezone.utc)` work on both backends.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
