from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserMemory
from app.errors import NotFound

# Caps how many memories get injected into the system prompt - keeps it from growing unbounded
# and eating the context window if a user accumulates hundreds of remembered facts over time.
MAX_MEMORIES_IN_PROMPT = 50


async def add_memory(db: AsyncSession, user: User, content: str) -> UserMemory:
    memory = UserMemory(user_id=user.id, content=content.strip())
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


async def list_memories(db: AsyncSession, user: User) -> list[UserMemory]:
    result = await db.execute(
        select(UserMemory).where(UserMemory.user_id == user.id).order_by(UserMemory.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_memory(db: AsyncSession, user: User, memory_id: str) -> None:
    memory = await db.get(UserMemory, memory_id)
    if memory is None or memory.user_id != user.id:
        raise NotFound("Erinnerung nicht gefunden.")
    await db.delete(memory)
    await db.commit()


async def memories_for_prompt(db: AsyncSession, user: User) -> list[str]:
    result = await db.execute(
        select(UserMemory.content)
        .where(UserMemory.user_id == user.id)
        .order_by(UserMemory.created_at.desc())
        .limit(MAX_MEMORIES_IN_PROMPT)
    )
    return list(result.scalars().all())
