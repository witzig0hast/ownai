import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now(timezone.utc).date()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    # "pending" | "approved" | "declined" - see app/api/auth.py. The first-ever registration
    # bootstraps straight to "approved" (same bootstrap as is_admin above); every later
    # registration starts "pending" until an admin approves/declines it (app/api/admin.py).
    approval_status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    devices: Mapped[list["Device"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    calendar_account: Mapped["CalendarAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    home_assistant_account: Mapped["HomeAssistantAccount | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    searxng_account: Mapped["SearxngAccount | None"] = relationship(
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
    automations: Mapped[list["Automation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    todo_lists: Mapped[list["TodoList"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    rss_feeds: Mapped[list["RssFeed"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    permanent_agents: Mapped[list["PermanentAgent"]] = relationship(
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


class SearxngAccount(Base):
    """One self-hosted SearXNG instance per user, for the web_search tool. No credentials field -
    unlike CalDAV/HA, a SearXNG instance's JSON search API is typically unauthenticated on the
    user's own network, so only the URL is stored."""

    __tablename__ = "searxng_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="searxng_account")


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


class Automation(Base):
    """Push the user when a Home Assistant entity reaches a given state (e.g. "warn me when the
    front door unlocks"). Edge-triggered, not level-triggered: `last_seen_state` records the state
    seen on the previous poll so the scheduler's _check_automations job (app/services/scheduler.py)
    only pushes on the transition INTO `trigger_state`, not on every poll while it stays there."""

    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_state: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    last_seen_state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="automations")


class TodoList(Base):
    """A named list (todo list or shopping list, distinguished by `kind`) holding checkable items.
    Named `TodoList` rather than `List` to avoid shadowing the builtin `list` used throughout this
    module's own type hints."""

    __tablename__ = "todo_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # todo | shopping
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="todo_lists")
    items: Mapped[list["TodoListItem"]] = relationship(
        back_populates="todo_list", cascade="all, delete-orphan", order_by="TodoListItem.created_at"
    )


class TodoListItem(Base):
    __tablename__ = "todo_list_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    list_id: Mapped[str] = mapped_column(String(36), ForeignKey("todo_lists.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(String(512), nullable=False)
    done: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    todo_list: Mapped["TodoList"] = relationship(back_populates="items")


class Expense(Base):
    """A single expense entry for the simple expense tracker ("gib 12,50€ für Mittagessen aus").
    No `updated_at`/edit support by design - correcting a mistake is delete-and-re-add, matching the
    scope of a lightweight log rather than a full accounting ledger. `amount` is a plain float
    (single implied currency, no multi-currency support) - fine for personal totals, not for
    anything that needs exact decimal accounting."""

    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    spent_at: Mapped[date] = mapped_column(Date, default=_today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="expenses")


class RssFeed(Base):
    """An RSS/Atom feed the user wants summarized ("was gibt's Neues bei X?"). No items are
    stored - every lookup fetches the feed live and hands the raw items to the chat/voice LLM,
    which does the actual summarizing as part of its normal response (same division of labor as
    calendar_list_events: the tool returns structured data, the assistant's own reply is the
    summary)."""

    __tablename__ = "rss_feeds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="rss_feeds")


class PermanentAgent(Base):
    """A named, recurring headless LLM agent ("Marktbeobachter") that wakes up on its own every
    `interval_minutes` (scheduler poll in app/services/scheduler.py, not a real always-on
    process - the LLM only runs during that one poll) and works a fixed, curated tool preset
    (`app/agent/agent_presets.py`) - never the full tool set, and never spawn_permanent_agent
    itself, so an unattended agent can't silently start creating further unattended agents. Its
    `role_prompt` is what makes two agents on the same preset behave differently (e.g. two
    web_watcher agents, one on "Bitcoin-Kurs", one on "Rust 2.0 Release News")."""

    __tablename__ = "permanent_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    preset: Mapped[str] = mapped_column(String(32), nullable=False)
    role_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    interval_minutes: Mapped[int] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="permanent_agents")
    log_entries: Mapped[list["AgentLogEntry"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", order_by="AgentLogEntry.created_at.desc()"
    )


class AgentLogEntry(Base):
    """One run's outcome for a PermanentAgent - what it found/did, and whether it judged the
    finding worth a push (`notable`, set via the agent's own flag_finding tool call, see
    permanent_agent_service.py). Findings accumulate here rather than in UserMemory because
    they're a per-agent timestamped feed to browse, not facts to inject into unrelated chats."""

    __tablename__ = "agent_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permanent_agents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notable: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    agent: Mapped["PermanentAgent"] = relationship(back_populates="log_entries")


class AppLog(Base):
    """General-purpose structured log entry, queryable via GET /logs (Settings -> Logs tab) so
    a user can see exactly what happened/went wrong for a given feature (e.g. "zeig mir alle
    E-Mail-Logs") without needing server/container access. Not a replacement for Python's
    stdlib `logging` (container stdout) - this is specifically for events worth surfacing to
    the user themselves, recorded via app/services/log_service.py."""

    __tablename__ = "app_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Nullable: most entries belong to the user whose action triggered them, but a handful of
    # background/system events (e.g. scheduler-level failures not tied to one user) may not.
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Short machine-readable source tag the frontend filters by, e.g. "email", "calendar",
    # "home_assistant" - deliberately a free string, not an enum, so new categories don't need
    # a migration.
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), default="info")  # info | warning | error
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    # Optional longer context (e.g. the raw exception text, which phase of an SMTP send failed)
    # kept separate from `message` so the list view can stay a short one-liner per entry.
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
