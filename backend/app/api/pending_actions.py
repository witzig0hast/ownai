from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.pending_action import PendingActionOut, PendingActionsListOut
from app.services import pending_action_service

router = APIRouter(prefix="/pending-actions", tags=["pending-actions"])


@router.get("", response_model=PendingActionsListOut)
async def list_pending_actions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendingActionsListOut:
    actions = await pending_action_service.list_pending(db, user)
    return PendingActionsListOut(pending_actions=actions)


@router.post("/{pending_id}/approve", response_model=PendingActionOut)
async def approve_pending_action(
    pending_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendingActionOut:
    return await pending_action_service.approve(db, user, pending_id)


@router.post("/{pending_id}/decline", response_model=PendingActionOut)
async def decline_pending_action(
    pending_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendingActionOut:
    return await pending_action_service.decline(db, user, pending_id)
