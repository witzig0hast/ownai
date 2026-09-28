from datetime import date, datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Contact, RecurringReminder, Timer, User
from app.db.session import async_session_maker
from app.services import push_service, scheduler

_WEEKDAY_BY_INDEX = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


async def test_expired_timer_triggers_push_once(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/timer", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    pushed = []
    monkeypatch.setattr(
        push_service,
        "_send_sync",
        lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None,
    )

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        timer = Timer(
            user_id=user.id,
            label="Nudeln",
            ends_at=datetime.now(timezone.utc) - timedelta(seconds=5),
        )
        db.add(timer)
        await db.commit()
        timer_id = timer.id

    await scheduler._check_expired_timers()

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/timer"
    assert payload["title"] == "Timer abgelaufen"
    assert payload["body"] == "Nudeln"

    async with async_session_maker() as db:
        refreshed = await db.get(Timer, timer_id)
        assert refreshed.notified is True

    # Running the poll again must not re-notify an already-notified timer.
    await scheduler._check_expired_timers()
    assert len(pushed) == 1


async def test_cancelled_timer_is_never_notified(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    pushed = []
    monkeypatch.setattr(
        push_service, "_send_sync", lambda subscription, payload: pushed.append(subscription.endpoint) or None
    )

    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        timer = Timer(
            user_id=user.id,
            label="Abgebrochen",
            ends_at=datetime.now(timezone.utc) - timedelta(seconds=5),
            cancelled=True,
        )
        db.add(timer)
        await db.commit()

    await scheduler._check_expired_timers()
    assert pushed == []


async def test_birthday_today_triggers_push_once(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/birthday", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    pushed = []
    monkeypatch.setattr(
        push_service,
        "_send_sync",
        lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None,
    )

    today = date.today()
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        contact = Contact(
            user_id=user.id, name="Anna Muster", birthday_month=today.month, birthday_day=today.day,
            birthday_year=today.year - 30,
        )
        db.add(contact)
        await db.commit()
        contact_id = contact.id

    await scheduler._check_birthdays()

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/birthday"
    assert payload["title"] == "Geburtstag"
    assert payload["body"] == "Anna Muster wird heute 30"

    async with async_session_maker() as db:
        refreshed = await db.get(Contact, contact_id)
        assert refreshed.last_birthday_push_date == today.isoformat()

    # Running the poll again on the same day must not re-notify.
    await scheduler._check_birthdays()
    assert len(pushed) == 1


async def test_contact_without_matching_birthday_is_not_notified(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    pushed = []
    monkeypatch.setattr(
        push_service, "_send_sync", lambda subscription, payload: pushed.append(subscription.endpoint) or None
    )

    other_day = (date.today().day % 28) + 1  # some day that (almost certainly) isn't today
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        db.add(Contact(user_id=user.id, name="Kein Geburtstag heute", birthday_month=1, birthday_day=other_day))
        await db.commit()

    await scheduler._check_birthdays()
    assert pushed == []


async def test_daily_reminder_due_now_triggers_push_once(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    await client.post(
        "/push/subscribe",
        json={"endpoint": "https://push.example/reminder", "keys": {"p256dh": "p", "auth": "a"}},
        headers=auth_headers,
    )

    pushed = []
    monkeypatch.setattr(
        push_service,
        "_send_sync",
        lambda subscription, payload: pushed.append((subscription.endpoint, payload)) or None,
    )

    now = datetime.now()
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        reminder = RecurringReminder(
            user_id=user.id, label="Wasser trinken", recurrence="daily", hour=now.hour, minute=now.minute
        )
        db.add(reminder)
        await db.commit()
        reminder_id = reminder.id

    await scheduler._check_recurring_reminders()

    assert len(pushed) == 1
    endpoint, payload = pushed[0]
    assert endpoint == "https://push.example/reminder"
    assert payload["title"] == "Erinnerung"
    assert payload["body"] == "Wasser trinken"

    async with async_session_maker() as db:
        refreshed = await db.get(RecurringReminder, reminder_id)
        assert refreshed.last_triggered_date == now.date().isoformat()

    # Running the poll again in the same minute must not re-notify.
    await scheduler._check_recurring_reminders()
    assert len(pushed) == 1


async def test_inactive_reminder_is_never_notified(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    pushed = []
    monkeypatch.setattr(
        push_service, "_send_sync", lambda subscription, payload: pushed.append(subscription.endpoint) or None
    )

    now = datetime.now()
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        db.add(
            RecurringReminder(
                user_id=user.id,
                label="Pausiert",
                recurrence="daily",
                hour=now.hour,
                minute=now.minute,
                active=False,
            )
        )
        await db.commit()

    await scheduler._check_recurring_reminders()
    assert pushed == []


async def test_weekly_reminder_on_wrong_weekday_is_not_notified(client: AsyncClient, auth_headers: dict, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "pub-key")
    monkeypatch.setattr(settings, "vapid_private_key", "priv-key")

    pushed = []
    monkeypatch.setattr(
        push_service, "_send_sync", lambda subscription, payload: pushed.append(subscription.endpoint) or None
    )

    now = datetime.now()
    other_weekday = _WEEKDAY_BY_INDEX[(now.weekday() + 1) % 7]
    async with async_session_maker() as db:
        user = (await db.execute(select(User))).scalar_one()
        db.add(
            RecurringReminder(
                user_id=user.id,
                label="Falscher Wochentag",
                recurrence="weekly",
                hour=now.hour,
                minute=now.minute,
                weekday=other_weekday,
            )
        )
        await db.commit()

    await scheduler._check_recurring_reminders()
    assert pushed == []
