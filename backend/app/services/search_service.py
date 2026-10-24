"""One search box over everything the user has in OwnAI: conversations (titles and message
text), memories, contacts, list items, reminders and expenses. Plain case-insensitive substring
matching (autoescaped, so % and _ in the query are literal) - no full-text index, which is fine
for a single person's data and keeps it identical on SQLite and Postgres."""

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Contact,
    Conversation,
    Expense,
    Message,
    RecurringReminder,
    TodoList,
    TodoListItem,
    User,
    UserMemory,
)

PER_TYPE_LIMIT = 8
SNIPPET_RADIUS = 60


def snippet(text: str, query: str) -> str:
    """The part of `text` around the first match, with ellipses where it was cut."""
    flat = " ".join(text.split())
    pos = flat.lower().find(query.lower())
    if pos < 0 or len(flat) <= 2 * SNIPPET_RADIUS:
        return flat[: 2 * SNIPPET_RADIUS] + ("…" if len(flat) > 2 * SNIPPET_RADIUS else "")
    start = max(0, pos - SNIPPET_RADIUS)
    end = min(len(flat), pos + len(query) + SNIPPET_RADIUS)
    return ("…" if start > 0 else "") + flat[start:end].strip() + ("…" if end < len(flat) else "")


def _like(column, query: str):
    return column.icontains(query, autoescape=True)


async def search(db: AsyncSession, user: User, query: str) -> list[dict[str, Any]]:
    q = query.strip()
    results: list[dict[str, Any]] = []

    # Conversations: a title hit, or the newest matching user/assistant message - one result per
    # conversation, so a word that appears in 30 messages doesn't flood the list.
    seen: set[str] = set()
    title_hits = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, _like(Conversation.title, q))
        .order_by(Conversation.updated_at.desc())
        .limit(PER_TYPE_LIMIT)
    )
    for conv in title_hits.scalars():
        seen.add(conv.id)
        results.append(
            {
                "type": "conversation",
                "id": conv.id,
                "title": conv.title or "Unbenannte Unterhaltung",
                "snippet": None,
                "href": f"/chat?c={conv.id}",
                "date": conv.updated_at.isoformat(),
            }
        )
    message_hits = await db.execute(
        select(Message, Conversation)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id, Message.role.in_(("user", "assistant")), _like(Message.content, q))
        .order_by(Message.created_at.desc())
        .limit(PER_TYPE_LIMIT * 4)
    )
    for message, conv in message_hits.all():
        if conv.id in seen or len(seen) >= PER_TYPE_LIMIT:
            continue
        seen.add(conv.id)
        results.append(
            {
                "type": "conversation",
                "id": conv.id,
                "title": conv.title or "Unbenannte Unterhaltung",
                "snippet": snippet(message.content, q),
                "href": f"/chat?c={conv.id}",
                "date": message.created_at.isoformat(),
            }
        )

    memories = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id, _like(UserMemory.content, q)).limit(PER_TYPE_LIMIT)
    )
    for m in memories.scalars():
        results.append(
            {
                "type": "memory",
                "id": m.id,
                "title": snippet(m.content, q),
                "snippet": None,
                "href": "/settings?tab=memory",
                "date": m.created_at.isoformat(),
            }
        )

    contacts = await db.execute(
        select(Contact)
        .where(
            Contact.user_id == user.id,
            or_(_like(Contact.name, q), _like(Contact.notes, q), _like(Contact.email, q), _like(Contact.phone, q)),
        )
        .limit(PER_TYPE_LIMIT)
    )
    for c in contacts.scalars():
        detail = next((v for v in (c.notes, c.email, c.phone) if v and q.lower() in v.lower()), None)
        results.append(
            {
                "type": "contact",
                "id": c.id,
                "title": c.name,
                "snippet": snippet(detail, q) if detail else None,
                "href": "/overview/contacts",
                "date": None,
            }
        )

    items = await db.execute(
        select(TodoListItem, TodoList)
        .join(TodoList, TodoListItem.list_id == TodoList.id)
        .where(TodoList.user_id == user.id, or_(_like(TodoListItem.content, q), _like(TodoList.name, q)))
        .limit(PER_TYPE_LIMIT)
    )
    for item, lst in items.all():
        results.append(
            {
                "type": "list_item",
                "id": item.id,
                "title": item.content,
                "snippet": f"{lst.name}{' · erledigt' if item.done else ''}",
                "href": "/overview/lists",
                "date": None,
            }
        )

    reminders = await db.execute(
        select(RecurringReminder)
        .where(RecurringReminder.user_id == user.id, _like(RecurringReminder.label, q))
        .limit(PER_TYPE_LIMIT)
    )
    for r in reminders.scalars():
        results.append(
            {
                "type": "reminder",
                "id": r.id,
                "title": r.label,
                "snippet": f"{r.hour:02d}:{r.minute:02d}",
                "href": "/overview/reminders",
                "date": None,
            }
        )

    expenses = await db.execute(
        select(Expense)
        .where(Expense.user_id == user.id, or_(_like(Expense.description, q), _like(Expense.category, q)))
        .order_by(Expense.spent_at.desc())
        .limit(PER_TYPE_LIMIT)
    )
    for e in expenses.scalars():
        amount = f"{e.amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        results.append(
            {
                "type": "expense",
                "id": e.id,
                "title": e.description,
                "snippet": f"{amount}{' · ' + e.category if e.category else ''}",
                "href": "/overview/expenses",
                "date": e.spent_at.isoformat(),
            }
        )

    return results
