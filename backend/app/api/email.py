from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.email import EmailConnectRequest, EmailConnectResponse, EmailStatusOut
from app.services import email_service

router = APIRouter(tags=["email"])


@router.post("/integrations/email", response_model=EmailConnectResponse)
async def connect_email(
    payload: EmailConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailConnectResponse:
    await email_service.connect(
        db,
        user,
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_username=payload.smtp_username,
        smtp_password=payload.smtp_password,
        from_address=payload.from_address,
        use_tls=payload.use_tls,
    )
    return EmailConnectResponse()


@router.get("/integrations/email", response_model=EmailStatusOut)
async def email_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailStatusOut:
    account = await email_service.get_account(db, user)
    if account is not None:
        return EmailStatusOut(has_custom_account=True, effective_from_address=account.from_address)

    config = await email_service.effective_config(db, user)
    return EmailStatusOut(
        has_custom_account=False,
        effective_from_address=config.from_address if config else None,
    )
