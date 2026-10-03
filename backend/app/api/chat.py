from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.agent.skills import SKILLS, is_valid_skill_key
from app.auth.dependencies import get_current_user, require_not_paused
from app.db.models import Conversation, Message, User
from app.db.session import async_session_maker, get_db
from app.errors import APIError, LlmUnavailable, NotFound
from app.schemas.chat import (
    ConversationCreateRequest,
    ConversationOut,
    ConversationsListOut,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageCreateResponse,
    MessagesListOut,
    SkillOut,
    SkillsListOut,
)
from app.schemas.files import GeneratedFilesListOut
from app.services import file_service, log_service, ollama_client
from app.services.ollama_client import OllamaError

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_owned_conversation(db: AsyncSession, user: User, conversation_id: str) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise NotFound("Unterhaltung nicht gefunden.")
    return conversation


async def _message_count(db: AsyncSession, conversation_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )
    return result.scalar_one()


@router.get("/conversations", response_model=ConversationsListOut)
async def list_conversations(
    include_archived: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationsListOut:
    query = select(Conversation).where(Conversation.user_id == user.id)
    if not include_archived:
        query = query.where(Conversation.archived.is_(False))
    query = query.order_by(Conversation.updated_at.desc())
    result = await db.execute(query)
    return ConversationsListOut(conversations=list(result.scalars().all()))


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conversation = Conversation(user_id=user.id, title=payload.title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    conversation = await _get_owned_conversation(db, user, conversation_id)
    if payload.title is not None:
        conversation.title = payload.title
    if payload.archived is not None:
        conversation.archived = payload.archived
    if payload.skill is not None:
        if not is_valid_skill_key(payload.skill):
            raise APIError(422, "invalid_skill", f"Unbekannter Skill: {payload.skill!r}.")
        conversation.skill = payload.skill
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/skills", response_model=SkillsListOut)
async def list_skills(_user: User = Depends(get_current_user)) -> SkillsListOut:
    return SkillsListOut(
        skills=[SkillOut(key=s.key, name=s.name, description=s.description) for s in SKILLS.values()]
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conversation = await _get_owned_conversation(db, user, conversation_id)
    await db.delete(conversation)
    await db.commit()


@router.post("/warmup", status_code=204)
async def warmup(_user: User = Depends(require_not_paused)) -> None:
    """Loads the LLM into memory ahead of time (see ollama_client.warmup) - clients call this
    when entering a screen that's about to need a fast first reply (Voice, Chat), so the model
    load doesn't happen on the critical path of the user's first message."""
    await ollama_client.warmup()


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesListOut)
async def list_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessagesListOut:
    conversation = await _get_owned_conversation(db, user, conversation_id)
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation.id).order_by(Message.created_at)
    )
    return MessagesListOut(messages=list(result.scalars().all()))


async def _generate_title_in_background(conversation_id: str, user_content: str, assistant_content: str) -> None:
    """Runs after the response has already gone to the client (see post_message) - title
    generation is itself a full extra Ollama call, no reason to make the user wait for it on
    top of the turn they're actually here for."""
    title = await ollama_client.generate_title(user_content, assistant_content)
    if not title:
        return
    async with async_session_maker() as db:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is not None and conversation.title is None:
            conversation.title = title
            await db.commit()


@router.post("/conversations/{conversation_id}/messages", response_model=MessageCreateResponse)
async def post_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    background_tasks: BackgroundTasks,
    stream: bool = Query(default=False),
    user: User = Depends(require_not_paused),
    db: AsyncSession = Depends(get_db),
) -> MessageCreateResponse:
    if stream:
        raise APIError(501, "not_implemented", "SSE-Streaming ist noch nicht implementiert (siehe API.md).")

    conversation = await _get_owned_conversation(db, user, conversation_id)
    needs_title = conversation.title is None and await _message_count(db, conversation.id) == 0

    try:
        assistant_message = await run_turn(db, user, conversation, payload.content)
    except OllamaError as exc:
        # Visible in Settings -> Logs ("chat") instead of just a dead end for the user - most
        # often means Ollama is unreachable or took too long to respond (slow/overloaded local
        # GPU), not a bug in this request itself.
        await log_service.log(
            db,
            category="chat",
            level="error",
            user=user,
            message="Antwort vom Sprachmodell fehlgeschlagen.",
            detail=str(exc),
        )
        raise LlmUnavailable() from exc

    if needs_title:
        background_tasks.add_task(
            _generate_title_in_background, conversation.id, payload.content, assistant_message.content
        )

    return MessageCreateResponse(message=assistant_message)


@router.get("/conversations/{conversation_id}/files", response_model=GeneratedFilesListOut)
async def list_conversation_files(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GeneratedFilesListOut:
    conversation = await _get_owned_conversation(db, user, conversation_id)
    files = await file_service.list_files(db, conversation)
    return GeneratedFilesListOut(files=files)


@router.get("/conversations/{conversation_id}/files/{file_id}")
async def download_conversation_file(
    conversation_id: str,
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    conversation = await _get_owned_conversation(db, user, conversation_id)
    record = await file_service.get_owned_file(db, user, conversation, file_id)
    disk_path = file_service.disk_path_for(user.id, conversation.id, record)
    if not disk_path.is_file():
        raise NotFound("Datei nicht gefunden.")
    return FileResponse(
        disk_path,
        media_type=record.mime_type,
        filename=record.filename,
    )
