from typing import Any

# Every tool NOT in this set is considered "consequential" by default (opt-in to safe, not
# opt-out of approval) - a skill with Skill.requires_approval=True (see skills.py) queues a call
# to any of these as a PendingAction instead of executing it, see app/agent/tool_execution.py.
# Kept to read-only/introspective tools plus low-stakes, easily-reversible utilities (timers).
# New tools default to requiring approval until explicitly added here.
SAFE_WITHOUT_APPROVAL: frozenset[str] = frozenset(
    {
        "agent_bus_list_agents",
        "calendar_list_events",
        "cancel_timer",
        "clip_url",
        "forget_fact",
        "get_weather",
        "home_assistant_list_entities",
        "list_agent_findings",
        "list_automations",
        "list_contacts",
        "list_expenses",
        "list_lists",
        "list_memories",
        "list_permanent_agents",
        "list_reminders",
        "list_rss_feeds",
        "list_rss_items",
        "list_timers",
        "remember_fact",
        "set_timer",
        # Delegating itself isn't consequential - the sub-agent loop it spawns goes through this
        # same gate for its own calls (see app/agent/tool_execution.py), so gating the spawn too
        # would just mean approving twice for one actual action.
        "spawn_subagent",
        "web_search",
    }
)


def requires_approval(tool_name: str) -> bool:
    return tool_name not in SAFE_WITHOUT_APPROVAL


def _format_args(arguments: dict[str, Any]) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in arguments.items())


def summarize_action(tool_name: str, arguments: dict[str, Any]) -> str:
    """One-line, human-readable description of a proposed tool call for the approval UI -
    covers the most common/sensitive tools by name, falls back to a generic rendering of the
    tool name + arguments for everything else rather than failing or needing to be exhaustive."""
    if tool_name == "send_email":
        return f"E-Mail an {arguments.get('to', '?')} senden (Betreff: \"{arguments.get('subject', '')}\")"
    if tool_name == "calendar_create_event":
        return f"Kalendertermin anlegen: \"{arguments.get('title', '?')}\""
    if tool_name == "home_assistant_call_service":
        return f"Smart-Home-Gerät steuern: {arguments.get('entity_id', '?')} -> {arguments.get('service', '?')}"
    if tool_name == "agent_bus_send_message":
        return f"Nachricht an Agent Bus \"{arguments.get('to_agent', '?')}\" senden"
    if tool_name.startswith("delete_"):
        thing = tool_name[len("delete_") :].replace("_", " ")
        return f"{thing.capitalize()} löschen ({_format_args(arguments)})"
    if tool_name.startswith("add_") or tool_name.startswith("create_"):
        thing = tool_name.split("_", 1)[1].replace("_", " ")
        return f"{thing.capitalize()} anlegen ({_format_args(arguments)})"
    if tool_name.startswith("update_"):
        thing = tool_name[len("update_") :].replace("_", " ")
        return f"{thing.capitalize()} ändern ({_format_args(arguments)})"
    return f"{tool_name}({_format_args(arguments)})"
