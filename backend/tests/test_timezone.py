from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.agent.orchestrator import _system_prompt
from app.agent.skills import get_skill
from app.config import get_settings
from app.utils import local_now


def test_local_now_uses_configured_zone(monkeypatch):
    monkeypatch.setattr(get_settings(), "timezone", "Europe/Berlin")
    now = local_now()
    assert now.tzinfo == ZoneInfo("Europe/Berlin")
    # Same instant as UTC now, just expressed in local wall-clock time.
    assert abs((now - datetime.now(timezone.utc)).total_seconds()) < 5


def test_system_prompt_gives_the_model_local_time_and_zone(monkeypatch):
    monkeypatch.setattr(get_settings(), "timezone", "Europe/Berlin")
    prompt = _system_prompt(get_skill("general"), [])
    assert "Europe/Berlin" in prompt
    assert "(UTC)" not in prompt


async def test_reminders_match_local_wall_clock_not_utc(client, auth_headers):
    """A reminder "um 8:30" must fire at 8:30 Berlin time - at that moment UTC says 6:30 or 7:30,
    which is exactly what the container clock reported before settings.timezone existed."""
    from app.db.session import async_session_maker
    from app.services import reminder_service

    await client.post(
        "/reminders",
        json={"label": "Tabletten", "recurrence": "daily", "hour": 8, "minute": 30, "weekday": None, "day_of_month": None},
        headers=auth_headers,
    )
    berlin_830 = datetime(2026, 7, 1, 8, 30, tzinfo=ZoneInfo("Europe/Berlin"))
    async with async_session_maker() as db:
        assert [r.label for r in await reminder_service.reminders_due_at(db, berlin_830)] == ["Tabletten"]
        utc_830 = berlin_830.replace(tzinfo=timezone.utc)
        assert await reminder_service.reminders_due_at(db, utc_830.astimezone(ZoneInfo("Europe/Berlin"))) == []
