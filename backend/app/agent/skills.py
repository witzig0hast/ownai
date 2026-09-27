from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    """A named bundle of a system-prompt focus + an optional tool subset. Lets the user narrow
    what the assistant pays attention to (and which tools it may call) per conversation, e.g. a
    "Zuhause" conversation that only ever touches Home Assistant/Timer, not email/calendar."""

    key: str
    name: str
    description: str
    prompt_addition: str
    # None = every tool in TOOL_SCHEMAS is available. A restricted skill both hides the other
    # tools' schemas from the model (so it doesn't try them) AND orchestrator.py refuses to
    # execute a call to a tool outside this set even if the model calls it anyway.
    tool_names: frozenset[str] | None


DEFAULT_SKILL_KEY = "general"

SKILLS: dict[str, Skill] = {
    "general": Skill(
        key="general",
        name="Allgemein",
        description="Der volle Assistent, alle Werkzeuge, kein besonderer Fokus.",
        prompt_addition="",
        tool_names=None,
    ),
    "home": Skill(
        key="home",
        name="Zuhause",
        description="Fokus auf Smart Home und Timer.",
        prompt_addition=(
            "Aktueller Fokus dieser Unterhaltung: Smart-Home-Steuerung und Timer. Antworte kurz und "
            "handlungsorientiert, wie eine Sprachsteuerung fürs Zuhause."
        ),
        tool_names=frozenset(
            {
                "home_assistant_list_entities",
                "home_assistant_call_service",
                "set_timer",
                "list_timers",
                "cancel_timer",
            }
        ),
    ),
    "organize": Skill(
        key="organize",
        name="Organisation",
        description="Fokus auf Kalender, Dateien und E-Mail.",
        prompt_addition=(
            "Aktueller Fokus dieser Unterhaltung: Termine, Dokumente und E-Mails. Hilf beim Planen, "
            "Verfassen und Verschicken."
        ),
        tool_names=frozenset(
            {"calendar_list_events", "calendar_create_event", "create_file", "send_email"}
        ),
    ),
}


def get_skill(key: str | None) -> Skill:
    return SKILLS.get(key or DEFAULT_SKILL_KEY, SKILLS[DEFAULT_SKILL_KEY])


def is_valid_skill_key(key: str) -> bool:
    return key in SKILLS
