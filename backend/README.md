# OwnAI Backend

FastAPI-Backend: Auth, Chat/Agent-Loop gegen Ollama, Kalender (CalDAV), Home Assistant (Smart-Home-Steuerung), Android-Notification-Ingestion + KI-Vorschläge, Sprach-Eingabe (Whisper/Wyoming). Implementiert exakt den Vertrag aus [`../API.md`](../API.md).

Für Sprach-Transkription (`POST /voice/transcribe`) wird `ffmpeg` benötigt (im Docker-Image bereits enthalten; für lokale Entwicklung außerhalb Docker: `apt install ffmpeg` bzw. Äquivalent).

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
pytest        # 27 Tests, laufen gegen eine temporäre SQLite-DB; Ollama/CalDAV/Home-Assistant sind gemockt,
              # der Wyoming/Whisper-Roundtrip läuft echt gegen einen Test-TCP-Server (kein Mock)
ruff check app tests
```

Beides lief in dieser Session tatsächlich grün (siehe Session-Zusammenfassung).

## Architektur

- `app/db/models.py` — SQLAlchemy-2.0-Modelle, dialektunabhängig gehalten (String-UUIDs, generisches JSON) — funktioniert identisch gegen SQLite (Tests/Dev) und Postgres (Prod).
- `app/agent/` — Tool-Loop: `orchestrator.py` ruft Ollama (`app/services/ollama_client.py`, natives `/api/chat` mit `tools`) auf, führt zurückgemeldete Tool-Calls über `app/agent/tools.py` aus (max. 5 Runden), persistiert am Ende eine einzelne Assistant-Message mit allen `tool_calls` (siehe `API.md`, bewusst kein Streaming in v1).
- `app/services/calendar_service.py` — CalDAV via `python-caldav`, Zugangsdaten Fernet-verschlüsselt in der DB (`app/services/crypto.py`, Schlüssel von `SECRET_KEY` abgeleitet).
- `app/services/home_assistant_service.py` — Home Assistant REST-API (`GET /api/states`, `POST /api/services/{domain}/{service}`) via `httpx`. Jeder Nutzer verbindet seine **eigene** HA-Instanz (kein globales Setup) — Long-Lived-Token Fernet-verschlüsselt gespeichert, analog zu CalDAV. `ALLOWED_DOMAINS` sperrt administrative HA-Domains (`homeassistant.*`, `shell_command`, `python_script`) für das LLM-Tool, damit der Agent nur unkritische Geräte (Licht, Steckdosen, Heizung, ...) steuern kann.
- `app/services/notification_service.py` — nimmt Android-Notifications entgegen, klassifiziert sie asynchron (FastAPI `BackgroundTasks`) per LLM-Prompt zu einem strikten JSON-Urteil, legt bei Relevanz eine `NotificationSuggestion` an. Warum eine Notification *keinen* Vorschlag erzeugt hat, ist jetzt im Backend-Log sichtbar statt komplett unsichtbar: `WARNING` mit dem rohen LLM-Output, wenn das Modell kein parsebares JSON liefert (häufigster Fehlerfall bei lokalen Modellen — sie ignorieren manchmal die "nur JSON"-Anweisung), `DEBUG`, wenn schlicht `relevant=false` klassifiziert wurde. Praktisch beim Debuggen von "Suggestions zeigt nie was an": `docker compose logs backend` nach dem Senden einer Test-Nachricht durchsuchen.
- `app/mcp_servers/` — dieselbe Kalender-/Notification-Logik zusätzlich als eigenständige MCP-Server (stdio) für externe MCP-Clients (z.B. Claude Desktop), unabhängig vom internen Tool-Loop-Pfad des Chat-Endpunkts (siehe Docstrings in den Dateien, warum beide Pfade bewusst getrennt sind).
- `app/services/whisper_client.py` — Speech-to-Text über eine bestehende Wyoming-ASR-Instanz (z.B. wyoming-whisper). Kein REST-API — Wyoming ist ein eigenes Event-Protokoll über eine rohe TCP-Verbindung (Python-Paket `wyoming`, siehe [github.com/rhasspy/wyoming](https://github.com/rhasspy/wyoming)). Empfangenes Audio (WebM/Opus, MP4/AAC, ...) wird per `ffmpeg`-Subprozess zu 16kHz-Mono-PCM dekodiert (das von Wyoming erwartete Format), dann als `Transcribe`→`AudioStart`→`AudioChunk`(s)→`AudioStop`-Event-Sequenz gesendet; die Antwort ist ein `Transcript`-Event mit dem erkannten Text.
- `app/services/file_service.py` — `create_file`-Tool (siehe `app/agent/tools.py`): rendert PDF (`fpdf2`, reines Python ohne System-Libs) oder speichert Text/Markdown, pro Nutzer/Unterhaltung unter `FILES_STORAGE_DIR`. **Sicherheitsdesign**: der Dateiname auf der Platte ist immer die server-generierte UUID der DB-Row, nie der vom LLM/Nutzer gelieferte `filename` (der ist rein Anzeige/`Content-Disposition`, sanitisiert) — dadurch ist Path-Traversal über einen manipulierten Dateinamen strukturell ausgeschlossen, nicht nur validiert.
- `app/services/email_service.py` — `send_email`-Tool. Nutzt stdlib `smtplib` (in `asyncio.to_thread`, da blockierend) statt einer Async-SMTP-Bibliothek, bewusst wegen der stabileren/besser dokumentierten Standard-API. Effektive Konfiguration: eigenes verbundenes SMTP-Konto des Nutzers (`POST /integrations/email`) > `SYSTEM_SMTP_*`-Umgebungsvariablen > `409 email_not_configured`.
- `app/services/vision_service.py` — `POST /vision/describe`: `ocr_image()` (Tesseract via `pytesseract`, deterministisch, kein LLM/Netzwerk nötig) und `describe_image()` (async, nur falls `OLLAMA_VISION_MODEL` gesetzt ist — sendet das Bild base64-kodiert an Ollamas natives multimodales `/api/chat`). Beide best-effort: liefern `null` statt eines Fehlers, wenn nicht verfügbar (fehlendes `tesseract-ocr`-Systempaket bzw. kein Vision-Modell konfiguriert).
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
- Wyoming/Whisper (`POST /voice/transcribe`): das Protokoll-Handling (`app/services/whisper_client.py`) läuft in `tests/test_whisper_client.py` echt über TCP gegen einen selbstgebauten Wyoming-Test-Server (inkl. echtem `ffmpeg`-Aufruf) — nicht nur gemockt. Trotzdem einmal gegen deine echte wyoming-whisper-Instanz testen (Sprachqualität, Latenz auf deiner P40 parallel zum LLM, tatsächliche Transkriptionsgüte auf Deutsch).
