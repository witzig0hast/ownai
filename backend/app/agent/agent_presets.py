from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPreset:
    """A fixed, curated tool set a permanent agent can be created with - deliberately not a free
    per-tool checklist (see PermanentAgent docstring for why): every preset is read-only/
    observational by construction, so an unattended headless loop can never silently send an
    email, book a calendar slot, or flip a smart-home switch. `tool_names` tools must never read
    `_conversation` in their handler (see permanent_agent_service.py), since permanent-agent runs
    have no Conversation to pass."""

    key: str
    name: str
    description: str
    tool_names: frozenset[str]


PRESETS: dict[str, AgentPreset] = {
    "web_watcher": AgentPreset(
        key="web_watcher",
        name="Web-Beobachter",
        description="Durchsucht das Web (SearXNG) und abonnierte RSS-Feeds nach Neuigkeiten zu einem Thema.",
        tool_names=frozenset({"web_search", "list_rss_feeds", "list_rss_items"}),
    ),
    "weather_watcher": AgentPreset(
        key="weather_watcher",
        name="Wetter-Wächter",
        description="Behält die Wetterlage für einen Ort im Auge.",
        tool_names=frozenset({"get_weather"}),
    ),
    "calendar_watcher": AgentPreset(
        key="calendar_watcher",
        name="Kalender-Wächter",
        description="Behält anstehende Termine im Auge.",
        tool_names=frozenset({"calendar_list_events"}),
    ),
    "home_watcher": AgentPreset(
        key="home_watcher",
        name="Home-Assistant-Wächter",
        description="Beobachtet den Zustand von Smart-Home-Geräten (nur lesend, keine Steuerung).",
        tool_names=frozenset({"home_assistant_list_entities"}),
    ),
}


def get_preset(key: str) -> AgentPreset | None:
    return PRESETS.get(key)


def is_valid_preset_key(key: str) -> bool:
    return key in PRESETS
