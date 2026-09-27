from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.memory import MemoriesListOut, MemoryCreateRequest, MemoryOut
from app.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryOut, status_code=201)
async def create_memory(
    payload: MemoryCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemoryOut:
    return await memory_service.add_memory(db, user, payload.content)


@router.get("", response_model=MemoriesListOut)
async def list_memories(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MemoriesListOut:
    memories = await memory_service.list_memories(db, user)
    return MemoriesListOut(memories=memories)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await memory_service.delete_memory(db, user, memory_id)
