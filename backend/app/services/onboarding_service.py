from pydantic import BaseModel
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CalendarAccount,
    Conversation,
    EmailAccount,
    HomeAssistantAccount,
    PushSubscription,
    SearxngAccount,
    User,
    UserMemory,
)
from app.services import push_service, sso_service


class SetupItem(BaseModel):
    key: str
    title: str
    description: str
    # Where the frontend sends the user to do it: a settings tab key (see
    # web/src/app/settings/page.tsx) or an app route.
    settings_tab: str | None = None
    href: str | None = None
    done: bool


async def _has(db: AsyncSession, model, user_id: str) -> bool:
    return bool(await db.scalar(select(exists().where(model.user_id == user_id))))


async def setup_items(db: AsyncSession, user: User) -> list[SetupItem]:
    items = [
        SetupItem(
            key="first_conversation",
            title="Erste Unterhaltung",
            description="Sag oder schreib dem Assistenten etwas - z.B. \"Was kannst du alles?\"",
            href="/voice",
            done=await _has(db, Conversation, user.id),
        ),
        SetupItem(
            key="memory",
            title="Erzähl ihm etwas über dich",
            description="Name, Wohnort, Vorlieben - der Assistent merkt sich das dauerhaft.",
            settings_tab="memory",
            done=await _has(db, UserMemory, user.id),
        ),
        SetupItem(
            key="calendar",
            title="Kalender verbinden",
            description="Per CalDAV, damit er Termine lesen und eintragen kann.",
            settings_tab="integrations",
            done=await _has(db, CalendarAccount, user.id),
        ),
        SetupItem(
            key="email",
            title="E-Mail-Konto hinterlegen",
            description="Damit Mails in deinem Namen rausgehen und er eingehende Mails bearbeiten kann.",
            settings_tab="email",
            done=await _has(db, EmailAccount, user.id),
        ),
        SetupItem(
            key="home_assistant",
            title="Home Assistant verbinden",
            description="Licht, Heizung & Co. per Sprache steuern.",
            settings_tab="integrations",
            done=await _has(db, HomeAssistantAccount, user.id),
        ),
        SetupItem(
            key="web_search",
            title="Web-Suche einrichten",
            description="Eigene SearXNG-Instanz, damit er aktuelle Infos nachschlagen kann.",
            settings_tab="integrations",
            done=await _has(db, SearxngAccount, user.id),
        ),
    ]
    # Only offered when the server can actually deliver them - otherwise these would be
    # permanently-unfinishable items the user can't do anything about.
    if push_service.is_push_configured():
        items.append(
            SetupItem(
                key="push",
                title="Push-Benachrichtigungen aktivieren",
                description="Für Timer, Erinnerungen und Rückfragen, auch wenn die App zu ist.",
                settings_tab="account",
                done=await _has(db, PushSubscription, user.id),
            )
        )
    if sso_service.is_configured():
        items.append(
            SetupItem(
                key="sso",
                title="Konto mit SSO verknüpfen",
                description="Danach kannst du dich auch über deinen Identity Provider anmelden.",
                settings_tab="account",
                done=user.sso_linked,
            )
        )
    return items
