from httpx import AsyncClient


async def test_register_and_list_devices(client: AsyncClient, auth_headers: dict):
    registered = await client.post(
        "/devices/register",
        json={"platform": "android", "label": "S25 Ultra", "push_token": None},
        headers=auth_headers,
    )
    assert registered.status_code == 201
    assert registered.json()["device_api_key"]

    listed = await client.get("/devices", headers=auth_headers)
    assert listed.status_code == 200
    devices = listed.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["platform"] == "android"
    assert devices[0]["label"] == "S25 Ultra"
    assert "device_api_key" not in devices[0]


async def test_list_devices_empty_by_default(client: AsyncClient, auth_headers: dict):
    listed = await client.get("/devices", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["devices"] == []
