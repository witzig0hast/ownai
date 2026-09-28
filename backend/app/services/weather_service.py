from typing import Any

import httpx

from app.errors import LocationNotFound, WeatherServiceError

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes (https://open-meteo.com/en/docs), condensed to short German
# descriptions. Any code not listed here (there are a few rare ones) falls back to "Unbekannt"
# rather than raising - a slightly vague forecast is better than a failed lookup.
_WEATHER_CODES: dict[int, str] = {
    0: "Klarer Himmel",
    1: "Überwiegend klar",
    2: "Teilweise bewölkt",
    3: "Bedeckt",
    45: "Nebel",
    48: "Nebel mit Reifbildung",
    51: "Leichter Nieselregen",
    53: "Mäßiger Nieselregen",
    55: "Starker Nieselregen",
    56: "Leichter gefrierender Niesel",
    57: "Starker gefrierender Niesel",
    61: "Leichter Regen",
    63: "Mäßiger Regen",
    65: "Starker Regen",
    66: "Leichter gefrierender Regen",
    67: "Starker gefrierender Regen",
    71: "Leichter Schneefall",
    73: "Mäßiger Schneefall",
    75: "Starker Schneefall",
    77: "Schneegriesel",
    80: "Leichte Regenschauer",
    81: "Mäßige Regenschauer",
    82: "Starke Regenschauer",
    85: "Leichte Schneeschauer",
    86: "Starke Schneeschauer",
    95: "Gewitter",
    96: "Gewitter mit leichtem Hagel",
    99: "Gewitter mit starkem Hagel",
}


def _describe(code: int) -> str:
    return _WEATHER_CODES.get(code, "Unbekannt")


def _client() -> httpx.AsyncClient:
    """Separate factory (rather than inlining httpx.AsyncClient() calls) purely so tests can
    monkeypatch it - same pattern as home_assistant_service._client."""
    return httpx.AsyncClient(timeout=15.0)


async def _geocode(city: str) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.get(
                GEOCODING_URL, params={"name": city, "count": 1, "language": "de", "format": "json"}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(f"Geocoding-Dienst nicht erreichbar: {exc}") from exc

    results = response.json().get("results")
    if not results:
        raise LocationNotFound(f"Ort {city!r} nicht gefunden.")
    return results[0]


async def _forecast(latitude: float, longitude: float) -> dict[str, Any]:
    async with _client() as client:
        try:
            response = await client.get(
                FORECAST_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                    "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                    "timezone": "auto",
                    "forecast_days": 3,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WeatherServiceError(f"Wetterdienst nicht erreichbar: {exc}") from exc
    return response.json()


async def weather_for_location(city: str) -> dict[str, Any]:
    place = await _geocode(city)
    forecast = await _forecast(place["latitude"], place["longitude"])

    current = forecast["current"]
    daily = forecast["daily"]
    return {
        "location": place["name"],
        "country": place.get("country"),
        "current_temperature": current["temperature_2m"],
        "current_condition": _describe(current["weather_code"]),
        "current_wind_speed": current["wind_speed_10m"],
        "daily": [
            {
                "date": daily["time"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "condition": _describe(daily["weather_code"][i]),
            }
            for i in range(len(daily["time"]))
        ],
    }
