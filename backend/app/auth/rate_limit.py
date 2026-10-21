import time
from collections import deque

from fastapi import Request

from app.config import get_settings
from app.errors import TooManyLoginAttempts

# In-process state on purpose: the backend runs as a single uvicorn process (see Dockerfile), and
# losing the counters on a restart only ever errs towards letting someone try again sooner. If
# this ever runs with several workers, this needs to move to the (already provisioned) Redis.
_failures_by_key: dict[tuple[str, str], deque[float]] = {}
_failures_by_email: dict[str, deque[float]] = {}


def client_ip(request: Request) -> str:
    header = get_settings().trusted_client_ip_header
    if header:
        value = request.headers.get(header)
        if value:
            # X-Forwarded-For can be a chain "client, proxy1, proxy2" - the first hop is the client.
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _prune(bucket: deque[float], now: float, window: float) -> None:
    while bucket and now - bucket[0] > window:
        bucket.popleft()


def check_allowed(email: str, ip: str) -> None:
    settings = get_settings()
    window = settings.login_failure_window_minutes * 60
    now = time.monotonic()
    email = email.lower()

    for bucket, limit in (
        (_failures_by_key.get((email, ip)), settings.login_max_failures),
        (_failures_by_email.get(email), settings.login_max_failures_per_email),
    ):
        if bucket is None:
            continue
        _prune(bucket, now, window)
        if len(bucket) >= limit:
            retry_after = int(window - (now - bucket[0])) + 1
            raise TooManyLoginAttempts(retry_after)


def record_failure(email: str, ip: str) -> None:
    now = time.monotonic()
    email = email.lower()
    _failures_by_key.setdefault((email, ip), deque()).append(now)
    _failures_by_email.setdefault(email, deque()).append(now)


def record_success(email: str, ip: str) -> None:
    _failures_by_key.pop((email.lower(), ip), None)


def reset() -> None:
    _failures_by_key.clear()
    _failures_by_email.clear()
