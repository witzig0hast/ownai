"""Standalone MCP server exposing the calendar tools over stdio.

Run with:  python -m app.mcp_servers.calendar_mcp --user-email you@example.com

This is for *external* MCP clients (Claude Desktop, other MCP-aware agents) that want to reuse the same
calendar logic the in-process chat agent uses (see app/agent/tools.py, which calls
app/services/calendar_service.py directly for speed — this server wraps the identical service functions
so both paths share one implementation and can never drift apart).

Since MCP tool calls aren't scoped to an HTTP request, the target user is fixed via --user-email at
startup (one server process per user is the simplest correct model for a personal, single/few-user system).
"""

import argparse
from datetime import datetime, timedelta, timezone

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

from app.db.models import User
from app.db.session import async_session_maker
from app.services import calendar_service
from app.utils import parse_iso_datetime

mcp = MCPServer("ownai-calendar")

_user_email: str | None = None


async def _load_user() -> User:
    if _user_email is None:
        raise RuntimeError("Server was not started with --user-email")
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == _user_email))
        user = result.scalar_one_or_none()
        if user is None:
            raise RuntimeError(f"No user found for email {_user_email!r}")
        return user


@mcp.tool()
async def calendar_list_events(start: str | None = None, end: str | None = None) -> list[dict]:
    """Listet Kalendertermine des Nutzers in einem Zeitraum (ISO-8601-Zeitstempel, Default: nächste 7 Tage)."""
    range_start = parse_iso_datetime(start) if start else datetime.now(timezone.utc)
    range_end = parse_iso_datetime(end) if end else range_start + timedelta(days=7)
    async with async_session_maker() as db:
        user = await _load_user()
        events = await calendar_service.list_events(db, user, range_start, range_end)
    return [{**e, "start": e["start"].isoformat(), "end": e["end"].isoformat()} for e in events]


@mcp.tool()
async def calendar_create_event(title: str, start: str, end: str | None = None, location: str | None = None) -> dict:
    """Legt einen neuen Kalendertermin an."""
    start_dt = parse_iso_datetime(start)
    end_dt = parse_iso_datetime(end) if end else start_dt + timedelta(hours=1)
    async with async_session_maker() as db:
        user = await _load_user()
        event = await calendar_service.create_event(db, user, title=title, start=start_dt, end=end_dt, location=location)
    return {**event, "start": event["start"].isoformat(), "end": event["end"].isoformat()}


def main() -> None:
    global _user_email
    parser = argparse.ArgumentParser(description="OwnAI calendar MCP server")
    parser.add_argument("--user-email", required=True, help="Email of the OwnAI user this server acts on behalf of")
    args = parser.parse_args()
    _user_email = args.user_email
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
