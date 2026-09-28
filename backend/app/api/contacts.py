from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.contact import ContactCreateRequest, ContactOut, ContactsListOut, ContactUpdateRequest
from app.services import contact_service

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post("", response_model=ContactOut, status_code=201)
async def create_contact(
    payload: ContactCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    return await contact_service.add_contact(db, user, payload)


@router.get("", response_model=ContactsListOut)
async def list_contacts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ContactsListOut:
    contacts = await contact_service.list_contacts(db, user)
    return ContactsListOut(contacts=contacts)


@router.patch("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: str,
    payload: ContactUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    return await contact_service.update_contact(db, user, contact_id, payload)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await contact_service.delete_contact(db, user, contact_id)
