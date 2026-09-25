# API-Vertrag v1

Verbindliche Schnittstelle zwischen `backend/` und den drei Clients (`web/`, `mobile/android/`, `mobile/ios/`). Jede Änderung hier erfordert ein Update in allen Clients.

- Base URL: `https://<host>/api/v1` (in Entwicklung: `http://localhost:8000/api/v1`)
- Format: JSON, `Content-Type: application/json`
- Auth: `Authorization: Bearer <access_token>` (JWT), außer bei `/auth/*` und dem Geräte-Ingestion-Endpoint (dort: `X-Device-Key: <device_api_key>`)
- Fehlerformat (immer, jeder Non-2xx-Status):
  ```json
  { "error": { "code": "invalid_credentials", "message": "E-Mail oder Passwort falsch." } }
  ```
- Zeitangaben: ISO-8601 UTC, z. B. `"2026-09-25T14:30:00Z"`
- IDs: UUID v4 als String, **immer lowercase** (so wie sie vom Server ausgegeben werden). ID-Vergleiche im Backend sind case-sensitive — ein Client, der eine empfangene ID zurück in einen Request/URL-Pfad einbaut, darf sie nicht hochcasen (z.B. Swifts `UUID.uuidString` liefert Großbuchstaben und muss vor Verwendung `.lowercased()` werden).

## Auth

### `POST /auth/register`
Request: `{ "email": string, "password": string (>=8 Zeichen), "display_name": string }`
Response `201`: `{ "id": uuid, "email": string, "display_name": string, "created_at": datetime }`
Fehler: `409 email_taken`

### `POST /auth/login`
Request: `{ "email": string, "password": string }`
Response `200`: `{ "access_token": string, "refresh_token": string, "token_type": "bearer", "expires_in": 900 }`
Fehler: `401 invalid_credentials`

Access-Token-TTL: 15 min. Refresh-Token-TTL: 30 Tage.

### `POST /auth/refresh`
Request: `{ "refresh_token": string }`
Response `200`: gleiche Form wie `/auth/login`
Fehler: `401 invalid_refresh_token`

### `GET /users/me`  *(Bearer)*
Response `200`: `{ "id": uuid, "email": string, "display_name": string, "created_at": datetime }`

## Geräte

### `POST /devices/register`  *(Bearer)*
Request: `{ "platform": "android" | "ios" | "web", "push_token": string | null, "label": string }`
Response `201`: `{ "id": uuid, "platform": string, "device_api_key": string, "label": string }`

`device_api_key` wird **nur bei Erstellung** zurückgegeben (danach nicht mehr abrufbar) und ausschließlich vom Android-Notification-Listener für `/notifications/ingest` verwendet — getrennt vom User-JWT, damit ein kompromittierter Gerätetoken nicht vollen Kontozugriff gibt.

## Chat

### `GET /chat/conversations`  *(Bearer)*
Response `200`: `{ "conversations": [ { "id": uuid, "title": string | null, "updated_at": datetime } ] }`

`title` is `null` until the conversation is explicitly named (a new conversation created without a title starts untitled — clients should render a fallback like "Untitled conversation").

### `POST /chat/conversations`  *(Bearer)*
Request: `{ "title": string | null }`
Response `201`: `{ "id": uuid, "title": string | null, "updated_at": datetime }`

### `GET /chat/conversations/{id}/messages`  *(Bearer)*
Response `200`: `{ "messages": [ Message ] }`

`Message`:
```json
{
  "id": "uuid",
  "role": "user" | "assistant" | "tool",
  "content": "string",
  "tool_calls": [ { "tool": "calendar.list_events", "arguments": {}, "result": {} } ] | null,
  "created_at": "datetime"
}
```

### `POST /chat/conversations/{id}/messages`  *(Bearer)*
Request: `{ "content": string }`
Response `200`: `{ "message": Message }` — **synchron**, d. h. der Request blockiert bis die Antwort (inkl. aller Tool-Aufrufe) fertig ist. Kein Streaming in v1 (siehe `CONCEPT.md`, bewusst zurückgestellt — SSE-Streaming ist als v2-Erweiterung vorgesehen, ohne Breaking Change an diesem Contract: es kommt ein zusätzlicher `stream=true` Query-Param, der aktuell `501 not_implemented` liefert, falls gesetzt).

## Kalender

### `POST /integrations/caldav`  *(Bearer)*
Request: `{ "url": string, "username": string, "password": string }`
Response `200`: `{ "connected": true }`
Anmeldedaten werden serverseitig **verschlüsselt** (Fernet, Schlüssel aus `SECRET_KEY`) gespeichert, nie im Klartext zurückgegeben.

### `GET /calendar/events?start={iso-datetime}&end={iso-datetime}`  *(Bearer)*

`start`/`end` are full ISO-8601 datetimes (UTC), same format as everywhere else in this document — not date-only strings.
Response `200`: `{ "events": [ { "id": string, "title": string, "start": datetime, "end": datetime, "location": string | null, "source": "caldav" } ] }`

### `POST /calendar/events`  *(Bearer)*
Request: `{ "title": string, "start": datetime, "end": datetime, "location": string | null }`
Response `201`: Event-Objekt wie oben

## Notifications (Android → Backend)

### `POST /notifications/ingest`  *(X-Device-Key)*
Request:
```json
{
  "package_name": "com.whatsapp",
  "app_label": "WhatsApp",
  "title": "Anna",
  "text": "Bist du heute Abend um 19 Uhr da?",
  "posted_at": "2026-09-25T18:02:00Z",
  "category": "msg" | "sms" | "other"
}
```
Response `202`: `{ "accepted": true, "notification_id": uuid }`

Verarbeitung läuft serverseitig asynchron (LLM prüft: kalenderrelevant? Antwortvorschlag sinnvoll?) und erzeugt ggf. einen Eintrag unter `/notifications/suggestions`.

### `GET /notifications/suggestions?status=open`  *(Bearer)*
Response `200`:
```json
{
  "suggestions": [
    {
      "id": "uuid",
      "notification_id": "uuid",
      "kind": "calendar_event" | "reply_draft",
      "summary": "Termin erkannt: heute 19 Uhr mit Anna",
      "payload": { "title": "Anna", "start": "2026-09-25T19:00:00Z", "end": "2026-09-25T20:00:00Z" },
      "status": "open" | "applied" | "dismissed",
      "created_at": "datetime"
    }
  ]
}
```

### `POST /notifications/suggestions/{id}/apply`  *(Bearer)*
Führt die Aktion aus (z. B. Kalendereintrag anlegen) und setzt `status=applied`. Response `200`: aktualisierter Suggestion-Eintrag.

### `POST /notifications/suggestions/{id}/dismiss`  *(Bearer)*
Response `200`: `{ "status": "dismissed" }`

## Health

### `GET /health`  *(kein Auth)*
Response `200`: `{ "status": "ok", "ollama": "ok" | "unreachable" }`
