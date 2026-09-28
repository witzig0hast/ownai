from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.list import (
    ListCreateRequest,
    ListItemCreateRequest,
    ListItemUpdateRequest,
    ListOut,
    ListsListOut,
    ListUpdateRequest,
)
from app.services import list_service

router = APIRouter(prefix="/lists", tags=["lists"])


@router.post("", response_model=ListOut, status_code=201)
async def create_list(
    payload: ListCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListOut:
    return await list_service.add_list(db, user, payload)


@router.get("", response_model=ListsListOut)
async def list_lists(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ListsListOut:
    lists = await list_service.list_lists(db, user)
    return ListsListOut(lists=lists)


@router.patch("/{list_id}", response_model=ListOut)
async def update_list(
    list_id: str,
    payload: ListUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListOut:
    return await list_service.update_list(db, user, list_id, payload)


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await list_service.delete_list(db, user, list_id)


@router.post("/{list_id}/items", response_model=ListOut, status_code=201)
async def add_item(
    list_id: str,
    payload: ListItemCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListOut:
    return await list_service.add_item(db, user, list_id, payload)


@router.patch("/{list_id}/items/{item_id}", response_model=ListOut)
async def update_item(
    list_id: str,
    item_id: str,
    payload: ListItemUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListOut:
    return await list_service.update_item(db, user, list_id, item_id, payload)


@router.delete("/{list_id}/items/{item_id}", response_model=ListOut)
async def delete_item(
    list_id: str, item_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ListOut:
    return await list_service.delete_item(db, user, list_id, item_id)
