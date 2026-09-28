from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contact, User
from app.errors import NotFound
from app.schemas.contact import ContactCreateRequest, ContactUpdateRequest


async def add_contact(db: AsyncSession, user: User, payload: ContactCreateRequest) -> Contact:
    contact = Contact(
        user_id=user.id,
        name=payload.name.strip(),
        phone=payload.phone,
        email=payload.email,
        birthday_month=payload.birthday_month,
        birthday_day=payload.birthday_day,
        birthday_year=payload.birthday_year,
        notes=payload.notes,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def list_contacts(db: AsyncSession, user: User) -> list[Contact]:
    result = await db.execute(select(Contact).where(Contact.user_id == user.id).order_by(Contact.name))
    return list(result.scalars().all())


async def _get_owned_contact(db: AsyncSession, user: User, contact_id: str) -> Contact:
    contact = await db.get(Contact, contact_id)
    if contact is None or contact.user_id != user.id:
        raise NotFound("Kontakt nicht gefunden.")
    return contact


async def update_contact(db: AsyncSession, user: User, contact_id: str, payload: ContactUpdateRequest) -> Contact:
    contact = await _get_owned_contact(db, user, contact_id)
    if payload.name is not None:
        contact.name = payload.name.strip()
    if payload.phone is not None:
        contact.phone = payload.phone
    if payload.email is not None:
        contact.email = payload.email
    if payload.birthday_month is not None:
        contact.birthday_month = payload.birthday_month
        contact.birthday_day = payload.birthday_day
    if payload.birthday_year is not None:
        contact.birthday_year = payload.birthday_year
    if payload.notes is not None:
        contact.notes = payload.notes
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(db: AsyncSession, user: User, contact_id: str) -> None:
    contact = await _get_owned_contact(db, user, contact_id)
    await db.delete(contact)
    await db.commit()


async def contacts_with_birthday_on(db: AsyncSession, today: date) -> list[Contact]:
    """Contacts of any user whose birthday_month/day matches `today` and who haven't already been
    pushed this year - used by the scheduler's daily birthday check (app/services/scheduler.py)."""
    today_iso = today.isoformat()
    result = await db.execute(
        select(Contact).where(
            Contact.birthday_month == today.month,
            Contact.birthday_day == today.day,
            or_(Contact.last_birthday_push_date.is_(None), Contact.last_birthday_push_date != today_iso),
        )
    )
    return list(result.scalars().all())
