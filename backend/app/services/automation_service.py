from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Automation, User
from app.errors import NotFound
from app.schemas.automation import AutomationCreateRequest, AutomationUpdateRequest


async def add_automation(db: AsyncSession, user: User, payload: AutomationCreateRequest) -> Automation:
    automation = Automation(
        user_id=user.id,
        entity_id=payload.entity_id.strip(),
        trigger_state=payload.trigger_state.strip(),
        message=payload.message.strip(),
    )
    db.add(automation)
    await db.commit()
    await db.refresh(automation)
    return automation


async def list_automations(db: AsyncSession, user: User) -> list[Automation]:
    result = await db.execute(
        select(Automation).where(Automation.user_id == user.id).order_by(Automation.created_at.desc())
    )
    return list(result.scalars().all())


async def list_active_automations(db: AsyncSession) -> list[Automation]:
    """All active automations across all users - used by the scheduler's poll
    (app/services/scheduler.py), which groups them by user to fetch each user's HA states once."""
    result = await db.execute(select(Automation).where(Automation.active.is_(True)))
    return list(result.scalars().all())


async def _get_owned_automation(db: AsyncSession, user: User, automation_id: str) -> Automation:
    automation = await db.get(Automation, automation_id)
    if automation is None or automation.user_id != user.id:
        raise NotFound("Automatisierung nicht gefunden.")
    return automation


async def update_automation(
    db: AsyncSession, user: User, automation_id: str, payload: AutomationUpdateRequest
) -> Automation:
    automation = await _get_owned_automation(db, user, automation_id)
    if payload.entity_id is not None:
        automation.entity_id = payload.entity_id.strip()
    if payload.trigger_state is not None:
        automation.trigger_state = payload.trigger_state.strip()
    if payload.message is not None:
        automation.message = payload.message.strip()
    if payload.active is not None:
        automation.active = payload.active
    await db.commit()
    await db.refresh(automation)
    return automation


async def delete_automation(db: AsyncSession, user: User, automation_id: str) -> None:
    automation = await _get_owned_automation(db, user, automation_id)
    await db.delete(automation)
    await db.commit()
