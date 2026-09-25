"""Standalone MCP server exposing read access to AI-generated notification suggestions over stdio.

Run with:  python -m app.mcp_servers.notifications_mcp --user-email you@example.com

Read-only by design: applying/dismissing a suggestion can have side effects (e.g. creating a calendar
event), which stays behind the authenticated REST API (see API.md) so every client goes through the same
audit-logged path rather than duplicating that logic here.
"""

import argparse

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

from app.db.models import NotificationSuggestion, User
from app.db.session import async_session_maker

mcp = MCPServer("ownai-notifications")

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
async def list_open_suggestions() -> list[dict]:
    """Listet offene, KI-generierte Vorschläge aus analysierten Benachrichtigungen (z.B. erkannte Termine)."""
    async with async_session_maker() as db:
        user = await _load_user()
        result = await db.execute(
            select(NotificationSuggestion)
            .where(NotificationSuggestion.user_id == user.id, NotificationSuggestion.status == "open")
            .order_by(NotificationSuggestion.created_at.desc())
        )
        suggestions = result.scalars().all()
    return [
        {
            "id": s.id,
            "kind": s.kind,
            "summary": s.summary,
            "payload": s.payload,
            "created_at": s.created_at.isoformat(),
        }
        for s in suggestions
    ]


def main() -> None:
    global _user_email
    parser = argparse.ArgumentParser(description="OwnAI notifications MCP server")
    parser.add_argument("--user-email", required=True, help="Email of the OwnAI user this server acts on behalf of")
    args = parser.parse_args()
    _user_email = args.user_email
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
