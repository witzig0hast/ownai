from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.consequential_tools import requires_approval, summarize_action
from app.db.models import Conversation, PendingAction, User
from app.errors import APIError


async def execute_tool_call(
    db: AsyncSession,
    user: User,
    conversation: Conversation,
    *,
    name: str,
    arguments: dict[str, Any],
    allowed_tool_names: frozenset[str] | None,
    not_available_message: str,
    gate_consequential: bool,
) -> Any:
    """Shared by orchestrator.run_turn and subagent.run_subagent, the two places a tool call
    actually gets dispatched - without this, a consequential-action approval gate added only to
    one of them could be bypassed via spawn_subagent (the email_inbox skill, which requires
    approval, has full tool access including spawn_subagent).

    `allowed_tool_names=None` means every registered tool is allowed (skill.tool_names's own
    convention). `gate_consequential=True` (only ever passed for Skill.requires_approval=True,
    i.e. currently only the "email_inbox" skill) queues a PendingAction instead of executing a
    tool in consequential_tools.SAFE_WITHOUT_APPROVAL's complement - see app/agent/skills.py for
    why: an autonomous trigger with nobody watching needs a confirm-before-acting step even
    though the user chose full tool access otherwise.
    """
    from app.agent.tools import TOOL_HANDLERS  # lazy: tools.py imports consequential_tools too

    handler = TOOL_HANDLERS.get(name)

    if allowed_tool_names is not None and name not in allowed_tool_names:
        return {"error": not_available_message}
    if handler is None:
        return {"error": f"Unbekanntes Werkzeug: {name}"}

    if gate_consequential and requires_approval(name):
        pending = PendingAction(
            user_id=user.id,
            conversation_id=conversation.id,
            tool_name=name,
            arguments=arguments,
            summary=summarize_action(name, arguments),
        )
        db.add(pending)
        await db.flush()
        return {
            "pending_approval": True,
            "pending_action_id": pending.id,
            "note": (
                "Diese Aktion wartet jetzt in der App auf Bestätigung durch den Nutzer und wurde noch "
                "NICHT ausgeführt. Sag dem Nutzer knapp, was du vorschlägst und dass es auf seine "
                "Bestätigung wartet - nicht, dass es bereits erledigt ist."
            ),
        }

    try:
        return await handler(db, user, conversation, arguments)
    except APIError as exc:
        return {"error": exc.message}
    except KeyError as exc:
        # A tool handler indexed a required argument the model didn't include
        # (arguments["foo"], not .get("foo")) - str(KeyError) is just the quoted key name
        # ("'foo'"), a cryptic message. Spell out what's actually wrong so the model can
        # immediately retry with a complete call instead of relaying the raw text.
        return {
            "error": (
                f"Pflicht-Parameter '{exc.args[0]}' fehlt beim Aufruf von '{name}'. "
                "Rufe das Werkzeug erneut mit allen benötigten Angaben auf."
            )
        }
    except Exception as exc:  # noqa: BLE001 - a tool failure must not crash the calling loop
        return {"error": str(exc)}
