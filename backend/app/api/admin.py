from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin import AdminUsersListOut, AppSettingsOut, AppSettingsUpdateRequest, UserApprovalRequest
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings", response_model=AppSettingsOut)
async def get_settings(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AppSettingsOut:
    settings = await admin_service.get_settings(db)
    return AppSettingsOut(
        registration_open=settings.registration_open,
        system_paused=settings.system_paused,
        system_paused_message=settings.system_paused_message,
    )


@router.patch("/settings", response_model=AppSettingsOut)
async def update_settings(
    payload: AppSettingsUpdateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AppSettingsOut:
    settings = await admin_service.update_settings(
        db,
        registration_open=payload.registration_open,
        system_paused=payload.system_paused,
        system_paused_message=payload.system_paused_message,
    )
    return AppSettingsOut(
        registration_open=settings.registration_open,
        system_paused=settings.system_paused,
        system_paused_message=settings.system_paused_message,
    )


@router.get("/users", response_model=AdminUsersListOut)
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUsersListOut:
    users = await admin_service.list_users(db)
    return AdminUsersListOut(users=users)


@router.get("/users/pending", response_model=AdminUsersListOut)
async def list_pending_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUsersListOut:
    users = await admin_service.list_pending_users(db)
    return AdminUsersListOut(users=users)


@router.patch("/users/{user_id}/approval", response_model=AdminUsersListOut)
async def set_user_approval(
    user_id: str,
    payload: UserApprovalRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUsersListOut:
    await admin_service.set_user_approval(db, user_id, payload.approval_status)
    # Returns the refreshed pending list (not just the one user) so the frontend can just
    # replace its list from the response, same shape as GET /admin/users/pending.
    users = await admin_service.list_pending_users(db)
    return AdminUsersListOut(users=users)
