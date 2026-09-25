# OwnAI Backend

FastAPI-Backend: Auth, Chat/Agent-Loop gegen Ollama, Kalender (CalDAV), Android-Notification-Ingestion + KI-Vorschläge. Implementiert exakt den Vertrag aus [`../API.md`](../API.md).

## Lokale Entwicklung

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp ../.env.example .env   # dann DATABASE_URL für lokale Entwicklung anpassen, z.B.:
# DATABASE_URL=sqlite+aiosqlite:///./ownai.db

python -m alembic upgrade head
uvicorn app.main:app --reload
```

Ohne laufendes Ollama antwortet `/api/v1/health` mit `"ollama": "unreachable"` — Chat-Anfragen schlagen dann mit einem 5xx von httpx fehl, alles andere (Auth, Kalender, Geräte) funktioniert unabhängig davon.

## Tests

```bash
pip install -r requirements-dev.txt
pytest        # 15 Tests, laufen gegen eine temporäre SQLite-DB, Ollama/CalDAV sind gemockt
ruff check app tests
```

Beides lief in dieser Session tatsächlich grün (siehe Session-Zusammenfassung).

## Architektur

- `app/db/models.py` — SQLAlchemy-2.0-Modelle, dialektunabhängig gehalten (String-UUIDs, generisches JSON) — funktioniert identisch gegen SQLite (Tests/Dev) und Postgres (Prod).
- `app/agent/` — Tool-Loop: `orchestrator.py` ruft Ollama (`app/services/ollama_client.py`, natives `/api/chat` mit `tools`) auf, führt zurückgemeldete Tool-Calls über `app/agent/tools.py` aus (max. 5 Runden), persistiert am Ende eine einzelne Assistant-Message mit allen `tool_calls` (siehe `API.md`, bewusst kein Streaming in v1).
- `app/services/calendar_service.py` — CalDAV via `python-caldav`, Zugangsdaten Fernet-verschlüsselt in der DB (`app/services/crypto.py`, Schlüssel von `SECRET_KEY` abgeleitet).
- `app/services/notification_service.py` — nimmt Android-Notifications entgegen, klassifiziert sie asynchron (FastAPI `BackgroundTasks`) per LLM-Prompt zu einem strikten JSON-Urteil, legt bei Relevanz eine `NotificationSuggestion` an.
- `app/mcp_servers/` — dieselbe Kalender-/Notification-Logik zusätzlich als eigenständige MCP-Server (stdio) für externe MCP-Clients (z.B. Claude Desktop), unabhängig vom internen Tool-Loop-Pfad des Chat-Endpunkts (siehe Docstrings in den Dateien, warum beide Pfade bewusst getrennt sind).
- Alle Fehler laufen über `app/errors.py` (`APIError`) durch zentrale Exception-Handler in `app/main.py` und liefern exakt `{"error": {"code", "message"}}` wie in `API.md` spezifiziert.

## Migrationen

Erste Migration (`alembic/versions/..._initial_schema.py`) wurde per `alembic revision --autogenerate` aus den Modellen erzeugt und gegen SQLite verifiziert. Für Postgres in Produktion: einfach `DATABASE_URL` auf `postgresql+asyncpg://...` setzen (siehe `.env.example`) und `alembic upgrade head` laufen lassen — keine SQLite-spezifischen Typen im Schema.

## MCP-Server manuell starten

```bash
python -m app.mcp_servers.calendar_mcp --user-email du@example.com
python -m app.mcp_servers.notifications_mcp --user-email du@example.com
```

## Bekannte Einschränkungen dieses Durchgangs

- Kein echter CalDAV-/Ollama-Server in dieser Session verfügbar — die entsprechenden Codepfade sind durch Unit-Tests mit gemockten Schnittstellen abgedeckt (siehe `tests/`), aber nicht gegen einen echten Server End-to-End getestet. Vor dem produktiven Einsatz einmal gegen deinen echten CalDAV-Account und ein laufendes Ollama testen.
- SSE-Streaming für Chat-Antworten ist bewusst noch nicht implementiert (`stream=true` liefert `501`, siehe `API.md`).
