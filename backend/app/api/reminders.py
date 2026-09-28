from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.reminder import ReminderCreateRequest, ReminderOut, ReminderUpdateRequest, RemindersListOut
from app.services import reminder_service

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=ReminderOut, status_code=201)
async def create_reminder(
    payload: ReminderCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.add_reminder(db, user, payload)


@router.get("", response_model=RemindersListOut)
async def list_reminders(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> RemindersListOut:
    reminders = await reminder_service.list_reminders(db, user)
    return RemindersListOut(reminders=reminders)


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.update_reminder(db, user, reminder_id, payload)


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await reminder_service.delete_reminder(db, user, reminder_id)
