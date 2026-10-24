from httpx import AsyncClient

from app.db.models import Message
from app.db.session import async_session_maker
from app.services.search_service import snippet


async def _other_user_headers(client: AsyncClient, admin_headers: dict) -> dict:
    await client.post("/auth/register", json={"email": "eve@example.com", "password": "eve-password", "display_name": "Eve"})
    pending = (await client.get("/admin/users/pending", headers=admin_headers)).json()["users"]
    await client.patch(f"/admin/users/{pending[0]['id']}/approval", json={"approval_status": "approved"}, headers=admin_headers)
    tokens = (await client.post("/auth/login", json={"email": "eve@example.com", "password": "eve-password"})).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _add_message(conversation_id: str, role: str, content: str) -> None:
    async with async_session_maker() as db:
        db.add(Message(conversation_id=conversation_id, role=role, content=content))
        await db.commit()


def _types(response) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in response.json()["results"]:
        out.setdefault(r["type"], []).append(r)
    return out


async def test_search_finds_every_kind_of_data(client: AsyncClient, auth_headers: dict):
    h = auth_headers
    conv = (await client.post("/chat/conversations", json={"title": "Urlaub Portugal"}, headers=h)).json()
    other = (await client.post("/chat/conversations", json={"title": "Sonstiges"}, headers=h)).json()
    await _add_message(other["id"], "user", "Wann fliegt der Flieger nach Lissabon, Portugal? " + "x" * 200)
    await _add_message(other["id"], "tool", "Portugal tool output must not be searched")
    await client.post("/memory", json={"content": "Lieblingsland ist Portugal"}, headers=h)
    await client.post("/contacts", json={"name": "Ana", "phone": None, "email": None, "birthday_month": None,
                                         "birthday_day": None, "birthday_year": None, "notes": "kennt Portugal gut"}, headers=h)
    lst = (await client.post("/lists", json={"name": "Packliste", "kind": "todo"}, headers=h)).json()
    await client.post(f"/lists/{lst['id']}/items", json={"content": "Reiseführer Portugal"}, headers=h)
    await client.post("/reminders", json={"label": "Portugal-Flug einchecken", "recurrence": "daily", "hour": 9,
                                          "minute": 5, "weekday": None, "day_of_month": None}, headers=h)
    await client.post("/expenses", json={"amount": 1234.5, "description": "Flug Portugal", "category": "Reisen",
                                         "spent_at": None}, headers=h)

    response = await client.get("/search/all", params={"q": "portugal"}, headers=h)
    assert response.status_code == 200
    by_type = _types(response)

    convs = {r["id"]: r for r in by_type["conversation"]}
    assert set(convs) == {conv["id"], other["id"]}
    assert convs[conv["id"]]["href"] == f"/chat?c={conv['id']}"
    assert "Lissabon, Portugal" in convs[other["id"]]["snippet"]
    assert by_type["memory"][0]["href"] == "/settings?tab=memory"
    assert by_type["contact"][0]["title"] == "Ana"
    assert by_type["contact"][0]["snippet"] == "kennt Portugal gut"
    assert by_type["list_item"][0]["snippet"] == "Packliste"
    assert by_type["reminder"][0]["snippet"] == "09:05"
    assert by_type["expense"][0]["snippet"] == "1.234,50 € · Reisen"


async def test_search_only_sees_own_data(client: AsyncClient, auth_headers: dict):
    await client.post("/memory", json={"content": "Geheimnis von Karim"}, headers=auth_headers)
    eve = await _other_user_headers(client, auth_headers)

    assert (await client.get("/search/all", params={"q": "Geheimnis"}, headers=eve)).json()["results"] == []
    assert len((await client.get("/search/all", params={"q": "Geheimnis"}, headers=auth_headers)).json()["results"]) == 1


async def test_search_treats_wildcards_literally(client: AsyncClient, auth_headers: dict):
    await client.post("/memory", json={"content": "Rabatt 50% bei Kauf"}, headers=auth_headers)
    await client.post("/memory", json={"content": "nichts Besonderes"}, headers=auth_headers)

    hits = (await client.get("/search/all", params={"q": "0%"}, headers=auth_headers)).json()["results"]
    assert [r["title"] for r in hits] == ["Rabatt 50% bei Kauf"]
    assert (await client.get("/search/all", params={"q": "__"}, headers=auth_headers)).json()["results"] == []


async def test_search_query_needs_two_characters(client: AsyncClient, auth_headers: dict):
    assert (await client.get("/search/all", params={"q": "a"}, headers=auth_headers)).status_code == 422
    assert (await client.get("/search/all", params={"q": "ab"})).status_code == 401


def test_snippet_centers_on_the_match():
    text = "a" * 100 + " Treffer " + "b" * 100
    s = snippet(text, "treffer")
    assert "Treffer" in s and s.startswith("…") and s.endswith("…")
    assert snippet("kurz", "kurz") == "kurz"
