from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import TodoList, TodoListItem, User
from app.errors import NotFound
from app.schemas.list import ListCreateRequest, ListItemCreateRequest, ListItemUpdateRequest, ListUpdateRequest

# Every read of a TodoList must eager-load `items` via selectinload - under the async engine, a
# relationship touched without eager loading (or an explicit db.refresh(obj, ["items"])) raises
# MissingGreenlet when the response model serializes it, since implicit lazy loading needs sync IO
# that the async driver can't do on demand.


async def add_list(db: AsyncSession, user: User, payload: ListCreateRequest) -> TodoList:
    todo_list = TodoList(user_id=user.id, name=payload.name.strip(), kind=payload.kind)
    db.add(todo_list)
    await db.commit()
    await db.refresh(todo_list, ["items"])
    return todo_list


async def list_lists(db: AsyncSession, user: User) -> list[TodoList]:
    result = await db.execute(
        select(TodoList)
        .where(TodoList.user_id == user.id)
        .options(selectinload(TodoList.items))
        .order_by(TodoList.created_at)
    )
    return list(result.scalars().unique().all())


async def _get_owned_list(db: AsyncSession, user: User, list_id: str) -> TodoList:
    result = await db.execute(
        select(TodoList).where(TodoList.id == list_id).options(selectinload(TodoList.items))
    )
    todo_list = result.scalar_one_or_none()
    if todo_list is None or todo_list.user_id != user.id:
        raise NotFound("Liste nicht gefunden.")
    return todo_list


async def update_list(db: AsyncSession, user: User, list_id: str, payload: ListUpdateRequest) -> TodoList:
    todo_list = await _get_owned_list(db, user, list_id)
    if payload.name is not None:
        todo_list.name = payload.name.strip()
    await db.commit()
    await db.refresh(todo_list, ["items"])
    return todo_list


async def delete_list(db: AsyncSession, user: User, list_id: str) -> None:
    todo_list = await _get_owned_list(db, user, list_id)
    await db.delete(todo_list)
    await db.commit()


async def add_item(db: AsyncSession, user: User, list_id: str, payload: ListItemCreateRequest) -> TodoList:
    todo_list = await _get_owned_list(db, user, list_id)
    item = TodoListItem(list_id=todo_list.id, content=payload.content.strip())
    db.add(item)
    await db.commit()
    await db.refresh(todo_list, ["items"])
    return todo_list


async def _get_owned_item(db: AsyncSession, user: User, list_id: str, item_id: str) -> TodoListItem:
    await _get_owned_list(db, user, list_id)  # raises NotFound if the list isn't the user's
    item = await db.get(TodoListItem, item_id)
    if item is None or item.list_id != list_id:
        raise NotFound("Eintrag nicht gefunden.")
    return item


async def update_item(
    db: AsyncSession, user: User, list_id: str, item_id: str, payload: ListItemUpdateRequest
) -> TodoList:
    item = await _get_owned_item(db, user, list_id, item_id)
    if payload.content is not None:
        item.content = payload.content.strip()
    if payload.done is not None:
        item.done = payload.done
    await db.commit()
    return await _get_owned_list(db, user, list_id)


async def delete_item(db: AsyncSession, user: User, list_id: str, item_id: str) -> TodoList:
    item = await _get_owned_item(db, user, list_id, item_id)
    await db.delete(item)
    await db.commit()
    return await _get_owned_list(db, user, list_id)
