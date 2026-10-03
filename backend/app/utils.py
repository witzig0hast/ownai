import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Any

# asyncio.create_task() does not itself keep its Task alive - with no other reference, it can be
# garbage-collected mid-run (a well-known asyncio footgun, see the "Important" note on
# create_task in the stdlib docs). Every fire_and_forget() task is held here until it finishes.
_background_tasks: set[asyncio.Task] = set()


def fire_and_forget(coro: Coroutine[Any, Any, Any]) -> None:
    """Schedules `coro` to run detached from the caller - the caller moves on immediately
    without awaiting it or seeing its result. Use only for work whose own outcome is reported
    elsewhere (e.g. logged via log_service) - there is nothing left to propagate a failure to
    once the caller has already returned."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


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
