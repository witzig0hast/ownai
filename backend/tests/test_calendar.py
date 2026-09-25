from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.services import calendar_service


class _FakeCalendar:
    def __init__(self):
        self.saved: list[str] = []

    def date_search(self, start, end):  # noqa: ARG002 - signature must match caldav.Calendar.date_search
        return []

    def save_event(self, ical: str):
        self.saved.append(ical)


@pytest.fixture(autouse=True)
def _patch_caldav(monkeypatch):
    fake_calendar = _FakeCalendar()
    monkeypatch.setattr(calendar_service, "_default_calendar", lambda account: fake_calendar)
    return fake_calendar


async def test_events_require_connected_calendar(client: AsyncClient, auth_headers: dict):
    response = await client.get("/calendar/events", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "calendar_not_connected"


async def test_connect_then_list_and_create_event(client: AsyncClient, auth_headers: dict, _patch_caldav):
    connect = await client.post(
        "/integrations/caldav",
        json={"url": "https://caldav.example.com/", "username": "karim", "password": "secret"},
        headers=auth_headers,
    )
    assert connect.status_code == 200
    assert connect.json() == {"connected": True}

    listed = await client.get("/calendar/events", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json() == {"events": []}

    created = await client.post(
        "/calendar/events",
        json={
            "title": "Zahnarzt",
            "start": "2026-10-01T09:00:00Z",
            "end": "2026-10-01T09:30:00Z",
            "location": "Praxis",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Zahnarzt"
    assert body["location"] == "Praxis"
    assert datetime.fromisoformat(body["start"]) == datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    assert len(_patch_caldav.saved) == 1
    assert "Zahnarzt" in _patch_caldav.saved[0]
