import re
from pathlib import Path
from typing import Literal

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Conversation, GeneratedFile, User
from app.errors import APIError

ALLOWED_FORMATS = {"pdf", "txt", "md"}
_MIME_TYPES = {"pdf": "application/pdf", "txt": "text/plain", "md": "text/markdown"}


class InvalidFileRequest(APIError):
    def __init__(self, message: str):
        super().__init__(422, "invalid_file_request", message)


class FileNotFound(APIError):
    def __init__(self, message: str = "Datei nicht gefunden."):
        super().__init__(404, "file_not_found", message)


def _sanitize_display_filename(filename: str) -> str:
    """For Content-Disposition / display only - the on-disk path never uses this (see
    _storage_dir/create_file), so there's no path-traversal risk here, just cosmetics."""
    name = Path(filename).name
    name = re.sub(r"[^\w\-. äöüÄÖÜß]", "_", name).strip()
    return name[:200] or "datei"


def _storage_dir(user_id: str, conversation_id: str) -> Path:
    settings = get_settings()
    base = Path(settings.files_storage_dir).resolve()
    directory = (base / user_id / conversation_id).resolve()
    # user_id/conversation_id are always our own UUIDs, never user/LLM input - this check is
    # defense in depth, not the primary safety mechanism.
    if directory != base and base not in directory.parents:
        raise InvalidFileRequest("Ungültiger Speicherpfad.")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _render_pdf(content: str, title: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.set_title(title)
    # The core PDF fonts (Helvetica et al.) only support Latin-1 - fine for German text
    # (umlauts/ß are representable), anything else falls back to "?" rather than erroring.
    safe_content = content.encode("latin-1", errors="replace").decode("latin-1")
    pdf.multi_cell(0, 6, safe_content)
    return bytes(pdf.output())


async def create_file(
    db: AsyncSession,
    user: User,
    conversation: Conversation,
    filename: str,
    content: str,
    file_format: Literal["pdf", "txt", "md"],
) -> GeneratedFile:
    settings = get_settings()
    if file_format not in ALLOWED_FORMATS:
        raise InvalidFileRequest(f"Format muss eines von {sorted(ALLOWED_FORMATS)} sein, war {file_format!r}.")
    if not content.strip():
        raise InvalidFileRequest("Inhalt darf nicht leer sein.")
    if len(content) > settings.files_max_content_chars:
        raise InvalidFileRequest(f"Inhalt zu lang (max. {settings.files_max_content_chars} Zeichen).")

    display_name = _sanitize_display_filename(filename)
    if not display_name.lower().endswith(f".{file_format}"):
        display_name = f"{display_name}.{file_format}"

    record = GeneratedFile(
        user_id=user.id,
        conversation_id=conversation.id,
        filename=display_name,
        mime_type=_MIME_TYPES[file_format],
        size_bytes=0,
    )
    db.add(record)
    await db.flush()  # assigns record.id, needed for the on-disk filename below

    data = _render_pdf(content, display_name) if file_format == "pdf" else content.encode("utf-8")
    disk_path = _storage_dir(user.id, conversation.id) / f"{record.id}.{file_format}"
    disk_path.write_bytes(data)
    record.size_bytes = len(data)

    await db.commit()
    await db.refresh(record)
    return record


def disk_path_for(user_id: str, conversation_id: str, record: GeneratedFile) -> Path:
    ext = record.filename.rsplit(".", 1)[-1] if "." in record.filename else "bin"
    return _storage_dir(user_id, conversation_id) / f"{record.id}.{ext}"


async def list_files(db: AsyncSession, conversation: Conversation) -> list[GeneratedFile]:
    result = await db.execute(
        select(GeneratedFile)
        .where(GeneratedFile.conversation_id == conversation.id)
        .order_by(GeneratedFile.created_at)
    )
    return list(result.scalars().all())


async def get_owned_file(db: AsyncSession, user: User, conversation: Conversation, file_id: str) -> GeneratedFile:
    record = await db.get(GeneratedFile, file_id)
    if record is None or record.user_id != user.id or record.conversation_id != conversation.id:
        raise FileNotFound()
    return record
