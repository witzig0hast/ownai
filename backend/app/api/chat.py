from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.auth.dependencies import get_current_user
from app.db.models import Conversation, Message, User
from app.db.session import get_db
from app.errors import APIError, NotFound
from app.schemas.chat import (
    ConversationCreateRequest,
    ConversationOut,
    ConversationsListOut,
    MessageCreateRequest,
    MessageCreateResponse,
    MessagesListOut,
)

router = APIRouter(prefix="/chat", tags=["chat"])


async def _get_owned_conversation(db: AsyncSession, user: User, conversation_id: str) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise NotFound("Unterhaltung nicht gefunden.")
    return conversation


@router.get("/conversations", response_model=ConversationsListOut)
async def list_conversations(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ConversationsListOut:
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc())
    )
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


@router.post("/conversations/{conversation_id}/messages", response_model=MessageCreateResponse)
async def post_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    stream: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageCreateResponse:
    if stream:
        raise APIError(501, "not_implemented", "SSE-Streaming ist noch nicht implementiert (siehe API.md).")

    conversation = await _get_owned_conversation(db, user, conversation_id)
    assistant_message = await run_turn(db, user, conversation, payload.content)
    return MessageCreateResponse(message=assistant_message)
