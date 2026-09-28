import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    devices: Mapped[list["Device"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    calendar_account: Mapped["CalendarAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    home_assistant_account: Mapped["HomeAssistantAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    timers: Mapped[list["Timer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    email_account: Mapped["EmailAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    agent_identities: Mapped[list["AgentIdentity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memories: Mapped[list["UserMemory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    recurring_reminders: Mapped[list["RecurringReminder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """DB-side record of an issued refresh token (identified by its JWT `jti`), so it can be revoked/rotated."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # == JWT jti
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)  # android | ios | web
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    push_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="devices")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archived: Mapped[bool] = mapped_column(default=False)
    # Which Skill (see app/agent/skills.py) this conversation uses - narrows the system prompt
    # focus and, for some skills, which tools the model is even offered.
    skill: Mapped[str] = mapped_column(String(32), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    files: Mapped[list["GeneratedFile"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant | tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class CalendarAccount(Base):
    __tablename__ = "calendar_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="calendar_account")


class HomeAssistantAccount(Base):
    """One Home Assistant instance per user (each user runs/owns their own HA, per the user)."""

    __tablename__ = "home_assistant_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="home_assistant_account")


class Timer(Base):
    """A simple countdown timer ("stell mir einen Timer auf 5 Minuten"), settable/cancelable via the
    chat/voice agent. Expiry is derived by clients comparing `ends_at` to now rather than tracked
    server-side — no scheduler needed here; each client (web tab, Android app) is responsible for
    noticing an active timer and surfacing it (see web's TimerBadge, Android's local AlarmManager)."""

    __tablename__ = "timers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled: Mapped[bool] = mapped_column(default=False)
    # Set by the proactive-notification scheduler (app/services/scheduler.py) once it has sent a
    # push for this timer's expiry, so it never notifies the same timer twice across polls.
    notified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="timers")


class PushSubscription(Base):
    """A single browser/device's Web Push subscription (endpoint URL + encryption keys, as
    returned by the browser's PushSubscription.toJSON()). A user can have several - one per
    browser/device they've enabled push on. See app/services/push_service.py for sending."""

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="push_subscriptions")


class GeneratedFile(Base):
    """A file the assistant created (e.g. a PDF) via the create_file tool, scoped to the user +
    conversation that requested it. The row's `id` is also the on-disk filename (see
    app/services/file_service.py) - the user-facing `filename` here is display-only and never
    touches the filesystem path, so nothing about it needs to be validated for path safety."""

    __tablename__ = "generated_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped["Conversation"] = relationship(back_populates="files")


class EmailAccount(Base):
    """Optional per-user SMTP override so the assistant sends email as the user's own address
    instead of the system-wide default (see app/services/email_service.py) - same 1:1-per-user
    pattern as CalendarAccount/HomeAssistantAccount."""

    __tablename__ = "email_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(nullable=False)
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_smtp_password: Mapped[str] = mapped_column(Text, nullable=False)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    use_tls: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="email_account")


class AppSettings(Base):
    """Single-row table (always id="singleton") holding system-wide admin settings. Created
    lazily on first access (see app/services/admin_service.py) rather than via a data
    migration, so a fresh install doesn't need a seed step."""

    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default="singleton")
    registration_open: Mapped[bool] = mapped_column(default=True)
    system_paused: Mapped[bool] = mapped_column(default=False)
    system_paused_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class NotificationRaw(Base):
    __tablename__ = "notifications_raw"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    app_label: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)  # msg | sms | other
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NotificationSuggestion(Base):
    __tablename__ = "notification_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    notification_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notifications_raw.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # calendar_event | reply_draft
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | applied | dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AgentIdentity(Base):
    """A registered external agent (one of the user's own other projects/websites) allowed to
    talk on this user's Agent Bus (see app/services/agent_bus_service.py). Scoped to a single
    OwnAI account - the bus is per-user, not a shared/global network between different OwnAI
    installs or users."""

    __tablename__ = "agent_identities"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_agent_identity_user_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="agent_identities")


class AgentMessage(Base):
    """One entry in the Agent Bus log - either a freeform text message or a structured task
    exchanged between registered agents (or the special "ownai" target, meaning the user/OwnAI
    itself). `from_label`/`to_label` are denormalized display names captured at send time, so
    the log stays readable even after an agent is renamed or removed."""

    __tablename__ = "agent_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_identities.id", ondelete="SET NULL"), nullable=True
    )
    from_label: Mapped[str] = mapped_column(String(64), nullable=False)
    to_agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_identities.id", ondelete="SET NULL"), nullable=True
    )
    to_label: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # text | task
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="sent")  # sent|pending|in_progress|completed|failed
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class UserMemory(Base):
    """A fact the assistant has learned about the user (the remember_fact tool, but can also be
    added/removed manually in Settings) - injected into every chat system prompt
    (orchestrator._system_prompt) so the assistant doesn't need to be told again."""

    __tablename__ = "user_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="memories")


class Contact(Base):
    """A person the user wants OwnAI to keep track of (name, birthday, contact details, notes). Birthday
    is stored as separate month/day/year columns rather than a single Date - month+day are what the
    scheduler's daily birthday check (app/services/scheduler.py) matches against "today", while year is
    optional (many people don't want to share/don't know it) and only used to show an age."""

    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birthday_month: Mapped[int | None] = mapped_column(nullable=True)
    birthday_day: Mapped[int | None] = mapped_column(nullable=True)
    birthday_year: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set to today's ISO date once a birthday push has been sent for this contact this year, so the
    # daily scheduler poll never sends the same birthday reminder twice.
    last_birthday_push_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="contacts")


class RecurringReminder(Base):
    """A reminder that fires repeatedly at a time of day (unlike Timer, which is a one-off countdown).
    `recurrence` picks which of weekday/day_of_month applies: "daily" uses neither, "weekly" needs
    weekday (3-letter, e.g. "mon"), "monthly" needs day_of_month (1-31). Matched against "now" every
    poll by the scheduler's _check_recurring_reminders job (app/services/scheduler.py) - the same
    poll-and-mark-done approach as Timer/Contact's birthday check, not a persisted APScheduler job, so
    it survives restarts without any re-registration step."""

    __tablename__ = "recurring_reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    recurrence: Mapped[str] = mapped_column(String(16), nullable=False)  # daily | weekly | monthly
    hour: Mapped[int] = mapped_column(nullable=False)
    minute: Mapped[int] = mapped_column(nullable=False)
    weekday: Mapped[str | None] = mapped_column(String(3), nullable=True)  # mon..sun, only for weekly
    day_of_month: Mapped[int | None] = mapped_column(nullable=True)  # 1-31, only for monthly
    active: Mapped[bool] = mapped_column(default=True)
    # Set to today's ISO date once fired today, so a minute-resolution poll never fires it twice.
    last_triggered_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="recurring_reminders")
