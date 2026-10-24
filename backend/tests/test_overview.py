from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from httpx import AsyncClient

from app.services import calendar_service, overview_service, push_service, scheduler, weather_service
from app.utils import local_now, local_today

BERLIN = ZoneInfo("Europe/Berlin")


def _reminder(**kw):
    base = {"recurrence": "daily", "hour": 8, "minute": 0, "weekday": None, "day_of_month": None}
    return SimpleNamespace(**{**base, **kw})


def test_next_reminder_daily_later_today_and_tomorrow():
    now = datetime(2026, 10, 21, 7, 0, tzinfo=BERLIN)  # a Wednesday
    assert overview_service.next_reminder_occurrence(_reminder(), now) == datetime(2026, 10, 21, 8, 0, tzinfo=BERLIN)
    late = now.replace(hour=9)
    assert overview_service.next_reminder_occurrence(_reminder(), late) == datetime(2026, 10, 22, 8, 0, tzinfo=BERLIN)


def test_next_reminder_weekly_and_monthly_skip_short_months():
    now = datetime(2026, 10, 21, 9, 0, tzinfo=BERLIN)
    weekly = overview_service.next_reminder_occurrence(_reminder(recurrence="weekly", weekday="mon"), now)
    assert weekly == datetime(2026, 10, 26, 8, 0, tzinfo=BERLIN)
    nov = datetime(2026, 11, 1, 9, 0, tzinfo=BERLIN)
    monthly = overview_service.next_reminder_occurrence(_reminder(recurrence="monthly", day_of_month=31), nov)
    assert monthly == datetime(2026, 12, 31, 8, 0, tzinfo=BERLIN)  # November has no 31st


def test_next_birthday_wraps_year_and_handles_29_february():
    today = date(2026, 12, 30)
    c = SimpleNamespace(birthday_month=1, birthday_day=2)
    assert overview_service.next_birthday(c, today) == date(2027, 1, 2)
    leap = SimpleNamespace(birthday_month=2, birthday_day=29)
    assert overview_service.next_birthday(leap, date(2026, 1, 1)) == date(2026, 2, 28)
    assert overview_service.next_birthday(SimpleNamespace(birthday_month=None, birthday_day=None), today) is None


async def _seed(client: AsyncClient, h: dict) -> None:
    lst = (await client.post("/lists", json={"name": "Einkauf", "kind": "shopping"}, headers=h)).json()
    for item in ["Milch", "Brot"]:
        lst = (await client.post(f"/lists/{lst['id']}/items", json={"content": item}, headers=h)).json()
    await client.patch(f"/lists/{lst['id']}/items/{lst['items'][0]['id']}", json={"done": True}, headers=h)
    soon = local_today() + timedelta(days=3)
    await client.post(
        "/contacts",
        json={"name": "Lisa", "phone": None, "email": None, "birthday_month": soon.month,
              "birthday_day": soon.day, "birthday_year": 1990, "notes": None},
        headers=h,
    )
    await client.post(
        "/contacts",
        json={"name": "Fern", "phone": None, "email": None, "birthday_month": None,
              "birthday_day": None, "birthday_year": None, "notes": None},
        headers=h,
    )
    await client.post("/expenses", json={"amount": 20.5, "description": "Tanken", "category": "Auto", "spent_at": None}, headers=h)
    await client.post("/expenses", json={"amount": 9.5, "description": "Kino", "category": "Freizeit", "spent_at": None}, headers=h)
    await client.post(
        "/reminders",
        json={"label": "Müll", "recurrence": "daily", "hour": 23, "minute": 59, "weekday": None, "day_of_month": None},
        headers=h,
    )


async def test_overview_aggregates_all_sections(client: AsyncClient, auth_headers: dict):
    await _seed(client, auth_headers)
    response = await client.get("/overview", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert body["display_name"] == "Karim"
    assert body["calendar"] == {"connected": False, "events": [], "error": None}
    assert body["lists"][0]["name"] == "Einkauf"
    assert body["lists"][0]["open_count"] == 1
    assert [i["content"] for i in body["lists"][0]["open_items"]] == ["Brot"]
    assert body["reminders"][0]["label"] == "Müll"
    assert [b["name"] for b in body["birthdays"]] == ["Lisa"]
    assert body["birthdays"][0]["days_until"] == 3
    assert body["expenses"]["month_total"] == 30.0
    assert body["expenses"]["by_category"][0] == {"category": "Auto", "total": 20.5}
    assert body["weather"] == {"home_city": None, "data": None, "error": None}
    assert body["pending_actions"] == 0


async def test_overview_weather_uses_home_city(client: AsyncClient, auth_headers: dict, monkeypatch):
    seen = []

    async def fake_weather(city):
        seen.append(city)
        return {"location": city, "current_temperature": 12.4, "current_condition": "bewölkt",
                "current_wind_speed": 10, "daily": [{"date": "x", "temp_min": 8.2, "temp_max": 14.6, "condition": "Regen"}]}

    monkeypatch.setattr(weather_service, "weather_for_location", fake_weather)
    await client.patch("/users/me", json={"home_city": "Berlin"}, headers=auth_headers)

    body = (await client.get("/overview", headers=auth_headers)).json()
    assert seen == ["Berlin"]
    assert body["weather"]["data"]["current_temperature"] == 12.4


async def test_a_failing_calendar_degrades_to_a_section_error(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_account(db, user):
        return object()

    def broken(*_args):
        raise ConnectionError("CalDAV server down")

    monkeypatch.setattr(calendar_service, "get_account", fake_account)
    monkeypatch.setattr(calendar_service, "_list_events_blocking", broken)

    response = await client.get("/overview", headers=auth_headers)
    assert response.status_code == 200
    cal = response.json()["calendar"]
    assert cal["connected"] is True
    assert "CalDAV server down" in cal["error"]


async def test_calendar_events_are_listed_for_today(client: AsyncClient, auth_headers: dict, monkeypatch):
    async def fake_account(db, user):
        return object()

    today = local_today()

    def events(_account, start, end):
        assert start.date() == today and end.date() == today
        at = lambda h: datetime(today.year, today.month, today.day, h, 0, tzinfo=BERLIN)  # noqa: E731
        return [
            {"title": "Zahnarzt", "start": at(15), "end": at(16), "location": None},
            {"title": "Standup", "start": at(9), "end": at(10), "location": "Büro"},
        ]

    monkeypatch.setattr(calendar_service, "get_account", fake_account)
    monkeypatch.setattr(calendar_service, "_list_events_blocking", events)

    cal = (await client.get("/overview", headers=auth_headers)).json()["calendar"]
    assert [e["title"] for e in cal["events"]] == ["Standup", "Zahnarzt"]


async def test_patch_me_updates_profile_and_briefing(client: AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/users/me",
        json={"home_city": "  Hamburg ", "briefing_enabled": True, "briefing_hour": 6, "briefing_minute": 45},
        headers=auth_headers,
    )
    assert response.status_code == 200
    me = response.json()
    assert me["home_city"] == "Hamburg"
    assert (me["briefing_enabled"], me["briefing_hour"], me["briefing_minute"]) == (True, 6, 45)

    cleared = (await client.patch("/users/me", json={"home_city": ""}, headers=auth_headers)).json()
    assert cleared["home_city"] is None
    assert cleared["briefing_hour"] == 6  # untouched fields stay

    assert (await client.patch("/users/me", json={"briefing_hour": 24}, headers=auth_headers)).status_code == 422


async def test_briefing_text_reads_naturally(client: AsyncClient, auth_headers: dict):
    await _seed(client, auth_headers)
    text = (await client.get("/overview/briefing", headers=auth_headers)).json()["text"]
    assert text.startswith("Guten Morgen, Karim.")
    assert "1 auf „Einkauf“" in text
    # No calendar connected -> the briefing doesn't claim "keine Termine".
    assert "Termin" not in text


def test_briefing_text_mentions_events_and_birthdays():
    overview = {
        "display_name": "Karim",
        "today": "2026-10-24",
        "weather": {"data": None},
        "calendar": {"connected": True, "error": None, "events": [
            {"title": "Standup", "start": "2026-10-24T09:00:00+02:00", "all_day": False},
            {"title": "Feiertag", "start": "2026-10-24T00:00:00+02:00", "all_day": True},
        ]},
        "reminders": [
            {"label": "Tabletten", "next_at": "2026-10-24T08:30:00+02:00"},
            {"label": "Müll", "next_at": "2026-10-26T19:00:00+01:00"},
        ],
        "birthdays": [{"name": "Lisa", "days_until": 0, "turns": 36}],
        "lists": [],
        "pending_actions": 2,
    }
    text = overview_service.briefing_text(overview)
    assert "Heute 2 Termine: um 09:00 Standup, Feiertag." in text
    assert "Erinnerungen heute: 08:30 Tabletten." in text  # Müll is Monday, not today
    assert "Lisa hat heute Geburtstag und wird 36." in text
    assert "2 Aktionen warten" in text


async def test_morning_briefing_is_pushed_once_at_the_chosen_time(client: AsyncClient, auth_headers: dict, monkeypatch):
    pushes = []

    async def fake_push(db, user, *, title, body, url=None):
        pushes.append((title, body, url))

    monkeypatch.setattr(push_service, "send_push", fake_push)
    await client.patch("/users/me", json={"briefing_enabled": True, "briefing_hour": 7, "briefing_minute": 0}, headers=auth_headers)

    seven = local_now().replace(hour=7, minute=0, second=5, microsecond=0)
    assert await scheduler.send_due_briefings(seven.replace(minute=1)) == []
    assert len(await scheduler.send_due_briefings(seven)) == 1
    assert pushes[0][0] == "Guten Morgen" and pushes[0][2] == "/overview"
    assert await scheduler.send_due_briefings(seven) == []  # not twice the same day


async def test_disabled_briefing_is_never_sent(client: AsyncClient, auth_headers: dict, monkeypatch):
    pushes = []

    async def fake_push(db, user, **kw):
        pushes.append(kw)

    monkeypatch.setattr(push_service, "send_push", fake_push)
    seven = local_now().replace(hour=7, minute=0)
    assert await scheduler.send_due_briefings(seven) == []
    assert pushes == []
