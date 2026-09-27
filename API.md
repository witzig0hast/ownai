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
Response `201`: `{ "id": uuid, "email": string, "display_name": string, "is_admin": bool, "created_at": datetime }`
Fehler: `409 email_taken`, `403 registration_closed` (Admin hat Registrierung geschlossen — betrifft nie den allerersten Nutzer überhaupt, der bootstrapt sich immer und wird automatisch `is_admin: true`)

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
Response `200`: `{ "id": uuid, "email": string, "display_name": string, "is_admin": bool, "created_at": datetime }`

## Geräte

### `POST /devices/register`  *(Bearer)*
Request: `{ "platform": "android" | "ios" | "web", "push_token": string | null, "label": string }`
Response `201`: `{ "id": uuid, "platform": string, "device_api_key": string, "label": string }`

`device_api_key` wird **nur bei Erstellung** zurückgegeben (danach nicht mehr abrufbar) und ausschließlich vom Android-Notification-Listener für `/notifications/ingest` verwendet — getrennt vom User-JWT, damit ein kompromittierter Gerätetoken nicht vollen Kontozugriff gibt.

## Chat

### `GET /chat/conversations?include_archived={bool}`  *(Bearer)*
Response `200`: `{ "conversations": [ { "id": uuid, "title": string | null, "archived": bool, "updated_at": datetime } ] }`

`title` is `null` until the conversation is explicitly named or auto-titled (see below). `include_archived` defaults to `false` — archived conversations are hidden from the default list.

### `POST /chat/conversations`  *(Bearer)*
Request: `{ "title": string | null }`
Response `201`: `{ "id": uuid, "title": string | null, "archived": bool, "updated_at": datetime }`

### `PATCH /chat/conversations/{id}`  *(Bearer)*
Request: `{ "title": string | null, "archived": bool | null }` — nur gesetzte Felder werden geändert. `title` kann per API nicht auf `null` zurückgesetzt werden (min. 1 Zeichen), nur umbenannt.
Response `200`: wie oben

### `DELETE /chat/conversations/{id}`  *(Bearer)*
Response `204`. Löscht die Unterhaltung inkl. aller Nachrichten endgültig (kein Soft-Delete — dafür gibt es `archived`).

### `POST /chat/warmup`  *(Bearer)*
Response `204`. Lädt das LLM in Ollama vor (`keep_alive`), ohne eine echte Antwort zu erzeugen — Clients rufen das beim Betreten eines Screens auf, der gleich eine schnelle erste Antwort braucht (Voice, Chat), damit das Laden des Modells nicht die erste echte Nachricht verzögert. Fehler bei Ollama werden intern verschluckt (best-effort), der Endpunkt liefert trotzdem `204`.
Fehler: `503 system_paused`.

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
Fehler: `503 system_paused` (Admin hat das System pausiert — `message` enthält ggf. einen vom Admin gesetzten Grund, siehe Admin-Sektion).

**Auto-Titel**: ist die Unterhaltung beim ersten Austausch (erste Nutzernachricht) noch unbenannt (`title: null`), generiert das Backend nach der Antwort automatisch einen kurzen Titel (per LLM, best-effort — schlägt die Generierung fehl, bleibt die Unterhaltung unbenannt, kein Fehler nach außen). Eine bereits explizit gesetzte `title` wird dadurch nie überschrieben.

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

## Home Assistant

Jeder Nutzer verbindet seine **eigene** Home-Assistant-Instanz — es gibt keine globale/geteilte HA-Konfiguration, genau wie bei CalDAV ist das ein 1:1-Zusammenhang pro User.

### `POST /integrations/home-assistant`  *(Bearer)*
Request: `{ "url": string, "token": string }` — `url` ist die Basis-URL der Home-Assistant-Instanz (z. B. `http://homeassistant.local:8123`), `token` ein Long-Lived Access Token aus dem HA-Profil des Nutzers.
Response `200`: `{ "connected": true }`
Der Token wird serverseitig **verschlüsselt** (Fernet, Schlüssel aus `SECRET_KEY`) gespeichert, nie im Klartext zurückgegeben.

### `GET /home-assistant/entities?domain={domain}`  *(Bearer)*
`domain` optional (z. B. `light`, `switch`, `climate`) — ohne Angabe werden alle Entities zurückgegeben.
Response `200`: `{ "entities": [ { "entity_id": string, "domain": string, "state": string | null, "friendly_name": string } ] }`

Fehler: `409 home_assistant_not_connected` (kein HA verbunden), `502 home_assistant_error` (HA nicht erreichbar oder hat den Request abgelehnt).

Steuern von Geräten (z. B. Licht an/aus) läuft nicht über einen eigenen REST-Endpunkt, sondern **über den Chat/Voice-Agenten**: das LLM ruft dafür die Tools `home_assistant_list_entities`/`home_assistant_call_service` auf (siehe `app/agent/tools.py`). Aus Sicherheitsgründen sind nur unkritische Domains erlaubt (`light`, `switch`, `climate`, `cover`, `fan`, `lock`, `media_player`, `scene`, `script`, `vacuum`, `humidifier`, `water_heater`, `input_boolean`) — administrative HA-Domains (`homeassistant.*`, `shell_command`, `python_script`) sind für das LLM gesperrt.

## Timer

Countdown-Timer ("stell mir einen Timer auf 5 Minuten"), settable/cancelable über den Chat/Voice-Agenten (Tools `set_timer`/`list_timers`/`cancel_timer`, siehe `app/agent/tools.py`) — es gibt keinen eigenen REST-Endpunkt zum *Anlegen*. Die beiden Endpunkte hier dienen Clients dazu, aktive Timer zu **anzeigen/abzubrechen** (z. B. eine Ecke der Web-App, die geräteübergreifend einen Countdown zeigt und beim Ablaufen benachrichtigt).

### `GET /timers`  *(Bearer)*
Response `200`: `{ "timers": [ { "id": string, "label": string | null, "ends_at": datetime } ] }` — alle nicht abgebrochenen Timer, **inklusive bereits abgelaufener** (`ends_at` in der Vergangenheit). Ob/wie ein abgelaufener Timer angezeigt wird, entscheidet der Client (`ends_at` mit der aktuellen Zeit vergleichen); der Server trackt keinen "expired"-Status.

### `POST /timers/{id}/cancel`  *(Bearer)*
Response `200`: Timer-Objekt wie oben. Fehler: `404 timer_not_found`.

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

## Sprache (Voice)

### `POST /voice/transcribe`  *(Bearer, multipart/form-data)*
Request: `multipart/form-data` mit Feld `audio` (Datei, beliebiges gängiges Audioformat — WebM/Opus, MP4/AAC, WAV etc.; das Backend dekodiert serverseitig via `ffmpeg`). Max. 25 MB.
Response `200`: `{ "text": string }`

Fehler: `400 empty_audio`, `413 audio_too_large`, `502 whisper_unavailable` (Whisper-Server nicht erreichbar/kein Transkript).

Reiner Speech-to-Text-Endpunkt — liefert nur den transkribierten Text zurück. Client schickt den Text danach ganz normal über `POST /chat/conversations/{id}/messages`. Text-to-Speech (Antworten vorlesen) läuft **client-seitig** über die jeweilige Plattform-API (Web: `speechSynthesis`, Android: `TextToSpeech`) — dafür gibt es keinen Backend-Endpunkt, da On-Device-TTS kostenlos, privat und ohne Server-Rundtrip funktioniert.

## Admin

Nur für Nutzer mit `is_admin: true` (siehe `/auth/register` — der allererste registrierte Nutzer überhaupt wird automatisch Admin, danach ist es eine feste Eigenschaft des Nutzers). Alle Endpunkte hier: `403 not_admin` für nicht-Admin-Nutzer.

Diese Endpunkte selbst sind **nie** vom `system_paused`-Zustand betroffen — sonst könnte ein pausiertes System von niemandem mehr entpausiert werden. Ebenso bleiben `/auth/login` und `/auth/refresh` immer erreichbar, auch pausiert.

### `GET /admin/settings`  *(Bearer, Admin)*
Response `200`: `{ "registration_open": bool, "system_paused": bool, "system_paused_message": string | null }`

### `PATCH /admin/settings`  *(Bearer, Admin)*
Request: `{ "registration_open": bool | null, "system_paused": bool | null, "system_paused_message": string | null }` — nur gesetzte Felder werden geändert.
Response `200`: wie `GET /admin/settings`

`system_paused: true` blockiert `POST /chat/conversations/{id}/messages` (der eigentliche Ollama/LLM-Traffic) mit `503 system_paused` für alle Nutzer — alle anderen Endpunkte (Kalender, Home Assistant, Timer, Login, ...) bleiben normal nutzbar.

### `GET /admin/users`  *(Bearer, Admin)*
Response `200`: `{ "users": [ { "id": uuid, "email": string, "display_name": string, "is_admin": bool, "created_at": datetime } ] }`

## Health

### `GET /health`  *(kein Auth)*
Response `200`: `{ "status": "ok", "ollama": "ok" | "unreachable" }`
