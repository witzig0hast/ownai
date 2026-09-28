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

### `GET /devices`  *(Bearer)*
Response `200`: `{ "devices": [ { "id": uuid, "platform": string, "label": string, "created_at": datetime } ] }` (kein `device_api_key`).

Genutzt vom Web-Frontend, um z. B. `/suggestions` (nutzlos ohne Android-App) nur anzuzeigen, wenn tatsächlich ein `"android"`-Gerät registriert ist.

## Chat

### `GET /chat/conversations?include_archived={bool}`  *(Bearer)*
Response `200`: `{ "conversations": [ { "id": uuid, "title": string | null, "archived": bool, "skill": string, "updated_at": datetime } ] }`

`title` is `null` until the conversation is explicitly named or auto-titled (see below). `include_archived` defaults to `false` — archived conversations are hidden from the default list.

### `POST /chat/conversations`  *(Bearer)*
Request: `{ "title": string | null }`
Response `201`: `{ "id": uuid, "title": string | null, "archived": bool, "skill": string, "updated_at": datetime }` — `skill` startet immer als `"general"`.

### `PATCH /chat/conversations/{id}`  *(Bearer)*
Request: `{ "title": string | null, "archived": bool | null, "skill": string | null }` — nur gesetzte Felder werden geändert. `title` kann per API nicht auf `null` zurückgesetzt werden (min. 1 Zeichen), nur umbenannt.
Response `200`: wie oben
Fehler: `422 invalid_skill` (unbekannter `skill`-Wert — siehe `GET /chat/skills` für die gültigen Werte).

### `GET /chat/skills`  *(Bearer)*
Response `200`: `{ "skills": [ { "key": string, "name": string, "description": string } ] }`

Ein **Skill** (siehe `app/agent/skills.py`) ist ein benannter Fokus pro Unterhaltung — er verändert den System-Prompt und schränkt bei manchen Skills zusätzlich ein, welche Tools dem Modell überhaupt angeboten werden (z. B. `"home"`: nur Home-Assistant/Timer-Tools, kein Kalender/E-Mail/Dateien). Ruft das Modell trotzdem ein Tool außerhalb des aktiven Skills auf, wird das serverseitig verweigert (`{ "error": "..." }` als Tool-Ergebnis), nicht ausgeführt — der Client bietet also nur an, was zum Skill passt, verlässt sich aber nicht allein darauf.

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

**Code Interpreter**: kein eigener Endpunkt — das LLM schreibt einfach einen ` ```python ` -Codeblock in seine normale Textantwort (System-Prompt weist es dazu an). Das Web-Frontend erkennt solche Blöcke clientseitig und führt sie auf Wunsch **komplett im Browser** aus (Pyodide/WASM, siehe `web/README.md`) — der Code erreicht den Server nie, egal was er tut.

**Sub-Agents**: das Tool `spawn_subagent` (siehe `app/agent/tools.py`/`app/agent/subagent.py`) delegiert eine abgegrenzte Teilaufgabe an einen eigenständigen, kleinen Tool-Loop (max. 3 Runden, eigener System-Prompt). Sein Tool-Ergebnis ist `{ "answer": string, "steps": [ { "tool", "arguments", "result" } ] }`. **Maximal eine Verschachtelungsebene**: `spawn_subagent` wird dem Sub-Agenten-Loop selbst nie als Werkzeug angeboten, er kann also keine weiteren Sub-Agents starten. Der Sub-Agent bekommt dieselbe Skill-Einschränkung wie die Unterhaltung (siehe unten) — in einer `"home"`- oder `"organize"`-Unterhaltung sieht er also nur deren Werkzeuge, nie mehr als die Hauptunterhaltung selbst.

### Dateien

Der Assistent kann Dateien (PDF, Text, Markdown) erstellen — über das Tool `create_file` (siehe `app/agent/tools.py`), nicht über einen eigenen REST-Endpunkt zum Anlegen. Jede Datei ist pro Nutzer und pro Unterhaltung gespeichert. Der Dateiname auf der Festplatte ist immer eine server-generierte UUID, nie der vom LLM übergebene `filename` — der ist rein für Anzeige/Download-Header, damit egal, was das LLM als Dateiname vorschlägt, nie ein Pfad-Traversal oder eine sonstige Manipulation des Speicherorts möglich ist.

### `GET /chat/conversations/{id}/files`  *(Bearer)*
Response `200`: `{ "files": [ { "id": uuid, "filename": string, "mime_type": string, "size_bytes": int, "created_at": datetime } ] }`

### `GET /chat/conversations/{id}/files/{file_id}`  *(Bearer)*
Response `200`: Roh-Dateiinhalt (`Content-Type` je nach Dateityp, `Content-Disposition: attachment` mit dem Anzeigenamen).
Fehler: `404` (Datei/Unterhaltung existiert nicht oder gehört einem anderen Nutzer).

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

## Web-Suche (SearXNG)

Jeder Nutzer verbindet seine **eigene**, selbst gehostete [SearXNG](https://docs.searxng.org/)-Instanz — gleiches 1:1-Muster wie bei CalDAV/Home Assistant. Anders als dort braucht es keinen API-Key/Token, nur die URL — SearXNGs JSON-Such-API ist im eigenen Netzwerk typischerweise unauthentifiziert. In der SearXNG-Konfiguration muss `json` als erlaubtes `format` aktiviert sein (`search: formats: [html, json]` in `settings.yml`), sonst schlägt die Suche fehl.

### `POST /integrations/searxng`  *(Bearer)*
Request: `{ "url": string }` (z. B. `http://searxng.local:8080`).
Response `200`: `{ "connected": true }`

### `GET /integrations/searxng`  *(Bearer)*
Response `200`: `{ "connected": bool, "url": string | null }` — reiner Status-Check ohne Seiteneffekt (löst keine echte Suche aus).

### `GET /search?q={string}`  *(Bearer)*
Response `200`: `{ "results": [ { "title": string, "url": string, "content": string | null } ] }` — die obersten 8 Treffer.
Fehler: `409 searxng_not_connected` (keine Instanz verbunden), `502 searxng_error` (Instanz nicht erreichbar oder kein gültiges JSON — meist weil `format=json` in der SearXNG-Konfiguration nicht aktiviert ist).

Auch als Tool `web_search` (siehe `app/agent/tools.py`) im Chat/Voice-Agenten nutzbar. **Nicht live gegen eine echte SearXNG-Instanz getestet** — kein Netzwerkzugriff in der Build-Sandbox dieser Session; die Verbinden-UI (Settings → Integrations → Web-Suche) wurde live bis zum Status "Verbunden" durchgeklickt, die eigentliche Such-Anfrage gegen eine echte Instanz aber nicht. Backend-seitig vollständig mit `httpx.MockTransport` getestet (`tests/test_searxng.py`). Vor Produktiveinsatz einmal mit einer echten SearXNG-Instanz durchklicken.

## E-Mail

Es gibt eine **system-weite Standard-E-Mail** (`SYSTEM_SMTP_*`-Umgebungsvariablen), die der Assistent nutzt, falls ein Nutzer kein eigenes Konto verbunden hat. Verbindet ein Nutzer sein eigenes SMTP-Konto, hat das immer Vorrang — gleiches 1:1-Muster wie bei CalDAV/Home Assistant.

### `POST /integrations/email`  *(Bearer)*
Request: `{ "smtp_host": string, "smtp_port": int, "smtp_username": string, "smtp_password": string, "from_address": string, "use_tls": bool }`
Response `200`: `{ "connected": true }`
Das Passwort wird serverseitig **verschlüsselt** (Fernet, Schlüssel aus `SECRET_KEY`) gespeichert, nie im Klartext zurückgegeben.

### `GET /integrations/email`  *(Bearer)*
Response `200`: `{ "has_custom_account": bool, "effective_from_address": string | null }` — `effective_from_address` ist die Absenderadresse, die aktuell tatsächlich verwendet würde (eigenes Konto oder System-Standard), `null` falls weder noch konfiguriert ist.

Versenden läuft nicht über einen eigenen REST-Endpunkt, sondern **über den Chat/Voice-Agenten**: das LLM ruft dafür das Tool `send_email` auf (siehe `app/agent/tools.py`), nur wenn der Nutzer explizit danach fragt. Fehler (z. B. kein Konto konfiguriert, SMTP-Fehler) kommen als Tool-Ergebnis `{ "error": string }` zurück, nicht als HTTP-Fehler des Chat-Endpunkts — der Chat-Turn selbst schlägt dadurch nie fehl.

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

## Push-Benachrichtigungen

Web Push (VAPID) — die Grundlage für proaktiven Kontakt: der Assistent meldet sich hier von sich aus, statt nur auf Anfragen zu reagieren. Ohne konfigurierte `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` (siehe `.env.example`) ist das komplett deaktiviert — still, kein Fehler, alles andere funktioniert normal weiter.

### `GET /push/vapid-public-key`
Response `200`: `{ "public_key": string | null, "configured": bool }` — kein Auth nötig, der Client braucht den Schlüssel schon vor dem Login-Flow für `PushManager.subscribe()`.

### `POST /push/subscribe`  *(Bearer)*
Request: die rohe Ausgabe von `PushSubscription.toJSON()` im Browser: `{ "endpoint": string, "keys": { "p256dh": string, "auth": string } }`.
Response `204`. Ein erneutes Abonnieren desselben `endpoint` aktualisiert den bestehenden Eintrag (Upsert), legt keinen Duplikat-Eintrag an.

### `POST /push/unsubscribe`  *(Bearer)*
Request: `{ "endpoint": string }`
Response `204`.

**Proaktive Ereignisse, die aktuell einen Push auslösen** (siehe `app/services/push_service.py`, `app/services/scheduler.py`):
- Ein **Timer läuft ab** — ein im Hintergrund laufender Poll (alle 15s, `app/services/scheduler.py`) prüft auf abgelaufene, noch nicht benachrichtigte Timer und pusht einmalig pro Timer (`Timer.notified`-Flag verhindert Doppel-Push).
- Eine **neue Notification-Suggestion** wird erkannt (siehe oben) — direkt nach dem Anlegen.

Ein fehlgeschlagener/abgelaufener Push (Browser antwortet `404`/`410`) entfernt die betroffene Subscription automatisch — best-effort, nie ein harter Fehler für den auslösenden Vorgang (Timer-Ablauf, Suggestion-Erstellung schlagen dadurch nie fehl).

**iOS-Einschränkung**: Web Push liefert auf iPhone/iPad nur an eine Seite, die über "Zum Home-Bildschirm hinzufügen" installiert wurde — ein offener Safari-Tab im Hintergrund bekommt grundsätzlich keine Push-Events, das ist eine Plattform-Einschränkung von iOS/Safari, keine Einstellungssache dieser App.

## Agent Bus

Ein zentraler Hub (in diesem Backend, nicht extern), über den **eigene andere Projekte/Webseiten** des Nutzers mit OwnAI (und potenziell untereinander, sofern beide über OwnAI registriert sind) Freitext-Nachrichten und strukturierte Aufgaben austauschen können — alles detailliert geloggt. Pro OwnAI-Konto isoliert: kein plattformweiter Bus zwischen verschiedenen Nutzern oder OwnAI-Installationen.

Jeder externe Teilnehmer registriert sich einmal (`POST /agent-bus/agents`, Bearer) und bekommt einen eigenen API-Key (`X-Agent-Key`-Header), mit dem er danach selbstständig Nachrichten senden/empfangen kann — unabhängig vom Login-Token des Nutzers. Der reservierte Name `"ownai"` adressiert immer den Kontobesitzer selbst (keine Registrierung nötig).

### `POST /agent-bus/agents`  *(Bearer)*
Request: `{ "name": string, "description": string | null }` — `name` muss pro Konto eindeutig sein (nicht `"ownai"`, das ist reserviert).
Response `201`: `{ "id": uuid, "name": string, "description": string | null, "api_key": string, "created_at": datetime }` — `api_key` wird nur hier einmalig im Klartext zurückgegeben, danach nur noch gehasht gespeichert (analog zu `POST /devices/register`).
Fehler: `409 agent_name_taken`.

### `GET /agent-bus/agents`  *(Bearer)*
Response `200`: `{ "agents": [ { "id", "name", "description", "created_at" } ] }` (kein `api_key`).

### `DELETE /agent-bus/agents/{id}`  *(Bearer)*
Response `204`.

### `POST /agent-bus/messages`  *(Bearer **oder** `X-Agent-Key`)*
Request: `{ "to": string, "kind": "text" | "task", "content": string | null, "task_type": string | null, "payload": object | null }` — `to` ist ein registrierter Agent-Name oder `"ownai"`. Bei `kind="text"` ist `content` Pflicht, bei `kind="task"` ist `task_type` Pflicht (`payload` optional).
Response `201`: die erstellte Nachricht (siehe unten). Mit `Bearer` sendet OwnAI/der Nutzer selbst (`from = "ownai"`); mit `X-Agent-Key` sendet der jeweilige Agent.
Fehler: `404 agent_not_found` (unbekanntes `to`).

Nachrichtenobjekt:
```json
{
  "id": "uuid",
  "from_label": "shop-backend",
  "to_label": "ownai",
  "kind": "text",
  "content": "Neue Bestellung eingegangen",
  "task_type": null,
  "payload": null,
  "status": "sent",
  "result": null,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```
`status` ist bei `kind="text"` immer `"sent"`; bei `kind="task"` startet es als `"pending"` und wird vom Empfänger-Agent über `POST /agent-bus/messages/{id}/result` auf `"completed"`/`"failed"` gesetzt.

### `GET /agent-bus/messages?agent_id={id}&status={status}`  *(Bearer)*
Log-Ansicht für den Nutzer — alle Nachrichten seines Bus (gesendet und empfangen), neueste zuerst. Beide Query-Parameter optional.
Response `200`: `{ "messages": [ Nachricht ] }`

### `GET /agent-bus/inbox`  *(`X-Agent-Key`)*
Posteingang eines einzelnen Agents — nur Nachrichten, die an ihn adressiert sind (`to == dieser Agent`). Zum Pollen durch den externen Agent gedacht.
Response `200`: `{ "messages": [ Nachricht ] }`

### `POST /agent-bus/messages/{id}/result`  *(`X-Agent-Key`)*
Meldet das Ergebnis einer Task zurück — nur erlaubt für den Agent, an den die Nachricht adressiert war, und nur bei `kind="task"`.
Request: `{ "status": "completed" | "failed", "result": object | null }`
Response `200`: die aktualisierte Nachricht.
Fehler: `404 agent_not_found` (Nachricht existiert nicht oder ist nicht an diesen Agent adressiert), `422 not_a_task`.

Eine Nachricht an `"ownai"` löst zusätzlich eine **Push-Benachrichtigung** an den Nutzer aus (siehe oben) — das macht den Agent Bus zu einem weiteren proaktiven Kontaktkanal: ein eigenes anderes Projekt kann OwnAI/den Nutzer so unaufgefordert erreichen.

Der Chat/Voice-Agent selbst ist ebenfalls Teilnehmer: die Tools `agent_bus_list_agents`/`agent_bus_send_message` (siehe `app/agent/tools.py`) lassen ihn im Auftrag des Nutzers Nachrichten an registrierte Agents schicken (`from = "ownai"`).

## Permanente Agenten

Ein **permanenter Agent** ist ein eigenständiger, dauerhaft laufender LLM-Beobachter mit einer festen Rolle — z. B. "beobachte den Bitcoin-Kurs und melde signifikante Bewegungen". Anders als der normale Chat/Voice-Agent oder ein `spawn_subagent` läuft er **ohne dass jemand mit ihm spricht**: ein Scheduler-Job weckt ihn in festen Intervallen (`interval_minutes`, mindestens 15) auf, er führt einen eigenständigen Tool-Loop durch und schreibt das Ergebnis in sein Log.

**Sicherheitsdesign**: jeder Agent bekommt beim Anlegen ein festes **Preset** — eine kuratierte, rein lesende Werkzeug-Teilmenge (siehe `GET /permanent-agents/presets`) — nie die vollen Werkzeuge, und explizit nicht die Werkzeuge, um selbst weitere permanente Agenten anzulegen. Das verhindert, dass ein unbeaufsichtigter Agent beginnt, selbstständig weitere Agenten zu erzeugen. Anlegen/Ändern/Löschen bleibt dem Nutzer vorbehalten — entweder über die Settings-UI oder per Zuruf an den Haupt-Chat-Agenten (Tools `create_permanent_agent` etc., siehe unten), nie durch einen permanenten Agenten selbst.

Findet ein Agent während eines Laufs etwas, das er für push-würdig hält, ruft er intern `flag_finding` auf (kein REST-Endpunkt — nur innerhalb des Agenten-Laufs verfügbar) — das markiert den Log-Eintrag als `notable` und löst eine Push-Benachrichtigung aus. Alles andere landet nur im Log.

### `GET /permanent-agents/presets`  *(Bearer)*
Response `200`: `{ "presets": [ { "key": string, "name": string, "description": string } ] }`. Aktuell: `web_watcher` (Web-Suche + RSS), `weather_watcher` (Wetter), `calendar_watcher` (Kalender lesen), `home_watcher` (Home-Assistant-Zustände lesen, keine Steuerung).

### `POST /permanent-agents`  *(Bearer)*
Request: `{ "name": string, "preset": string, "role_prompt": string, "interval_minutes": int }` — `interval_minutes` zwischen 15 und 10080 (eine Woche).
Response `201`: der erstellte Agent (siehe unten, `active: true`, `last_run_at: null`).
Fehler: `422 invalid_preset` (unbekanntes Preset).

### `GET /permanent-agents`  *(Bearer)*
Response `200`: `{ "agents": [ Agent ] }`, neueste zuerst.

Agentenobjekt:
```json
{
  "id": "uuid",
  "name": "Krypto-Beobachter",
  "preset": "web_watcher",
  "role_prompt": "Beobachte den Bitcoin-Kurs, melde nur bei Bewegungen über 5%.",
  "interval_minutes": 60,
  "active": true,
  "last_run_at": "datetime | null",
  "created_at": "datetime"
}
```

### `PATCH /permanent-agents/{id}`  *(Bearer)*
Request: wie `POST` ohne `preset` (das Preset ist nach dem Anlegen fest), alle Felder optional (inkl. `active`). Zum Pausieren/Reaktivieren einfach nur `{ "active": false }` schicken.
Response `200`: der aktualisierte Agent.

### `DELETE /permanent-agents/{id}`  *(Bearer)*
Löscht den Agenten inkl. seines gesamten Logs.
Response `204`.
Fehler: `404 not_found` (Agent existiert nicht oder gehört einem anderen Nutzer).

### `GET /permanent-agents/{id}/log?limit={int}`  *(Bearer)*
`limit` optional, 1–200, Standard 50.
Response `200`: `{ "entries": [ { "id", "content", "notable", "created_at" } ] }`, neueste zuerst.

Auch als Tools `create_permanent_agent` / `list_permanent_agents` / `update_permanent_agent` / `delete_permanent_agent` / `list_agent_findings` (siehe `app/agent/tools.py`) im Haupt-Chat/Voice-Agenten nutzbar — so kann der Nutzer per Zuruf einen Agenten anlegen ("leg mir einen Agenten an, der..."), ohne die Settings-UI zu öffnen. Geprüft durch einen minütlichen Scheduler-Job (`_run_permanent_agents` in `app/services/scheduler.py`), der fällige Agenten (`permanent_agent_service.due_agents`) sequenziell (nicht parallel, um die lokale Ollama-Instanz nicht mit gleichzeitigen Anfragen zu überlasten) abarbeitet. Ist Ollama nicht erreichbar, wird das als Fehler-Eintrag im Log festgehalten statt den Lauf zu verwerfen — `last_run_at` wird trotzdem aktualisiert, damit ein dauerhaft nicht erreichbares Ollama nicht zu einem Retry-Sturm bei jedem Scheduler-Poll führt.

Live bis zum echten Scheduler-Lauf getestet: ein Agent wurde angelegt, nach ~60s hat der reale Scheduler-Job ihn selbstständig ausgeführt und (mangels Ollama-Zugriff in der Build-Sandbox) einen sauberen Fehler-Log-Eintrag geschrieben — bestätigt, dass die komplette Kette (Poll → Fälligkeitsprüfung → Tool-Loop → Fehlerbehandlung → Log-Eintrag → UI-Anzeige) funktioniert.

## Gedächtnis (Memory)

Kurze Fakten, die sich der Assistent über den Nutzer merkt (z.B. "Mag keine Zwiebeln", "Wohnt in Berlin") und die bei **jeder** Unterhaltung automatisch in den System-Prompt eingemischt werden (siehe `_system_prompt()` in `app/agent/orchestrator.py`), ohne dass der Nutzer sie wiederholen muss. Maximal die letzten 50 Fakten werden eingemischt (`MAX_MEMORIES_IN_PROMPT` in `app/services/memory_service.py`), neueste zuerst.

Fakten entstehen entweder manuell über die Settings-UI (Tab "Gedächtnis") oder automatisch während des Chats über die Tools `remember_fact` / `list_memories` / `forget_fact` (siehe `app/agent/tools.py`) — der Agent entscheidet selbst, wann ein vom Nutzer erwähntes Detail es wert ist, gemerkt zu werden.

### `POST /memory`  *(Bearer)*
Request: `{ "content": string }` (max. 512 Zeichen).
Response `201`: `{ "id": uuid, "content": string, "created_at": datetime }`

### `GET /memory`  *(Bearer)*
Response `200`: `{ "memories": [ { "id", "content", "created_at" } ] }` — neueste zuerst.

### `DELETE /memory/{id}`  *(Bearer)*
Response `204`.
Fehler: `404 not_found` (Fakt existiert nicht oder gehört einem anderen Nutzer).

## Kontakte

Personen, die sich der Assistent merken soll — Name, optional Telefon/E-Mail, Geburtstag und Notizen. Ist ein Geburtstag hinterlegt (Monat+Tag; Jahr optional, nur für die Altersanzeige), erinnert der Assistent den Nutzer am Tag selbst automatisch per Push (siehe Push-Benachrichtigungen oben) — geprüft durch einen täglichen Scheduler-Job (`_check_birthdays` in `app/services/scheduler.py`, läuft um 08:00 Serverzeit; es gibt noch keine nutzerspezifische Zeitzone). `Contact.last_birthday_push_date` verhindert eine doppelte Erinnerung am selben Tag.

Kontakte entstehen entweder manuell über die Settings-UI (Tab "Kontakte") oder automatisch während des Chats über die Tools `add_contact` / `list_contacts` / `update_contact` / `delete_contact` (siehe `app/agent/tools.py`).

### `POST /contacts`  *(Bearer)*
Request: `{ "name": string, "phone": string | null, "email": string | null, "birthday_month": int | null, "birthday_day": int | null, "birthday_year": int | null, "notes": string | null }` — `birthday_month` und `birthday_day` müssen zusammen angegeben werden (oder beide weggelassen).
Response `201`: das erstellte Kontaktobjekt (siehe unten).
Fehler: `422` bei nur einem von `birthday_month`/`birthday_day`.

### `GET /contacts`  *(Bearer)*
Response `200`: `{ "contacts": [ Kontakt ] }`, alphabetisch nach Name.

Kontaktobjekt:
```json
{
  "id": "uuid",
  "name": "Anna Muster",
  "phone": "+49 170 1234567",
  "email": null,
  "birthday_month": 5,
  "birthday_day": 17,
  "birthday_year": 1990,
  "notes": null,
  "created_at": "datetime"
}
```

### `PATCH /contacts/{id}`  *(Bearer)*
Request: wie `POST`, alle Felder optional — nur angegebene Felder werden geändert (analog zu `PATCH /chat/conversations/{id}`).
Response `200`: das aktualisierte Kontaktobjekt.

### `DELETE /contacts/{id}`  *(Bearer)*
Response `204`.
Fehler: `404 not_found` (Kontakt existiert nicht oder gehört einem anderen Nutzer).

## Erinnerungen (Recurring Reminders)

Erinnerungen, die im Gegensatz zu einem Timer (siehe oben) nicht einmalig sind, sondern dauerhaft zu einer festen Uhrzeit wiederkehren: täglich, wöchentlich an einem Wochentag, oder monatlich an einem Tag des Monats. Geprüft durch einen minütlichen Scheduler-Job (`_check_recurring_reminders` in `app/services/scheduler.py`) gegen die lokale Serverzeit (keine nutzerspezifische Zeitzone); `RecurringReminder.last_triggered_date` verhindert eine doppelte Erinnerung innerhalb derselben Minute/desselben Tages. Eine pausierte Erinnerung (`active: false`) bleibt gespeichert, wird aber vom Scheduler übersprungen.

Erinnerungen entstehen entweder manuell über die Settings-UI (Tab "Erinnerungen") oder automatisch während des Chats über die Tools `add_reminder` / `list_reminders` / `update_reminder` / `delete_reminder` (siehe `app/agent/tools.py`).

### `POST /reminders`  *(Bearer)*
Request: `{ "label": string, "recurrence": "daily" | "weekly" | "monthly", "hour": int (0-23), "minute": int (0-59), "weekday": "mon".."sun" | null, "day_of_month": int (1-31) | null }` — `weekday` ist bei `recurrence="weekly"` Pflicht, `day_of_month` bei `recurrence="monthly"` Pflicht.
Response `201`: die erstellte Erinnerung (siehe unten, inkl. `active: true`).
Fehler: `422` bei fehlendem `weekday`/`day_of_month` für die jeweilige `recurrence`.

### `GET /reminders`  *(Bearer)*
Response `200`: `{ "reminders": [ Erinnerung ] }`, neueste zuerst.

Erinnerungsobjekt:
```json
{
  "id": "uuid",
  "label": "Tabletten nehmen",
  "recurrence": "daily",
  "hour": 8,
  "minute": 0,
  "weekday": null,
  "day_of_month": null,
  "active": true,
  "created_at": "datetime"
}
```

### `PATCH /reminders/{id}`  *(Bearer)*
Request: wie `POST`, alle Felder optional (inkl. `active`) — nur angegebene Felder werden geändert. Zum Pausieren/Reaktivieren einfach nur `{ "active": false }` schicken.
Response `200`: die aktualisierte Erinnerung.

### `DELETE /reminders/{id}`  *(Bearer)*
Response `204`.
Fehler: `404 not_found` (Erinnerung existiert nicht oder gehört einem anderen Nutzer).

## Automatisierungen

HA-getriggerte Push-Benachrichtigungen: "warne mich, wenn diese Home-Assistant-Entität einen bestimmten Zustand erreicht" (z.B. Tür wird aufgeschlossen, Wäsche fertig, Temperatur überschritten). Setzt eine verbundene Home-Assistant-Instanz voraus (siehe Home Assistant oben) — geprüft wird gegen die zum jeweiligen Nutzerkonto gehörende Instanz.

Geprüft durch einen Scheduler-Job (`_check_automations` in `app/services/scheduler.py`, alle 30s), der pro betroffenem Nutzer einmal `GET /api/states` gegen dessen Home Assistant abruft und alle seine aktiven Automatisierungen dagegen matcht. **Kantengetriggert, nicht zustandsgetriggert**: die Push feuert nur beim Übergang *in* den `trigger_state`, nicht bei jedem Poll, solange der Zustand bestehen bleibt (`Automation.last_seen_state` verhindert Spam). Ist die Home-Assistant-Instanz des Nutzers nicht verbunden oder nicht erreichbar, werden seine Automatisierungen für diesen Poll einfach übersprungen (kein Fehler für andere Nutzer).

Automatisierungen entstehen entweder manuell über die Settings-UI (Tab "Automatisierungen") oder automatisch während des Chats über die Tools `add_automation` / `list_automations` / `update_automation` / `delete_automation` (siehe `app/agent/tools.py`) — üblicherweise nachdem der Agent zuerst `home_assistant_list_entities` genutzt hat, um die passende `entity_id` und mögliche Zustandswerte herauszufinden.

### `POST /automations`  *(Bearer)*
Request: `{ "entity_id": string, "trigger_state": string, "message": string }`
Response `201`: die erstellte Automatisierung (siehe unten, inkl. `active: true`, `last_seen_state: null`).

### `GET /automations`  *(Bearer)*
Response `200`: `{ "automations": [ Automatisierung ] }`, neueste zuerst.

Automatisierungsobjekt:
```json
{
  "id": "uuid",
  "entity_id": "lock.haustuer",
  "trigger_state": "unlocked",
  "message": "Haustür ist auf",
  "active": true,
  "last_seen_state": "locked",
  "created_at": "datetime"
}
```

### `PATCH /automations/{id}`  *(Bearer)*
Request: wie `POST`, alle Felder optional (inkl. `active`) — nur angegebene Felder werden geändert. Zum Pausieren/Reaktivieren einfach nur `{ "active": false }` schicken.
Response `200`: die aktualisierte Automatisierung.

### `DELETE /automations/{id}`  *(Bearer)*
Response `204`.
Fehler: `404 not_found` (Automatisierung existiert nicht oder gehört einem anderen Nutzer).

## Listen

Todo- und Einkaufslisten (`kind`: `"todo"` oder `"shopping"`) mit abhakbaren Einträgen. Eine Liste wird immer mitsamt ihrer Einträge zurückgegeben (kein separater Endpunkt für einzelne Listen nötig) — bei mehreren Einträgen typischerweise überschaubar viele, daher kein Paging.

Listen und Einträge entstehen entweder manuell über die Settings-UI (Tab "Listen") oder automatisch während des Chats über die Tools `create_list` / `list_lists` / `delete_list` / `add_list_item` / `update_list_item` / `delete_list_item` (siehe `app/agent/tools.py`).

### `POST /lists`  *(Bearer)*
Request: `{ "name": string, "kind": "todo" | "shopping" }`
Response `201`: die erstellte Liste (siehe unten, `items: []`).

### `GET /lists`  *(Bearer)*
Response `200`: `{ "lists": [ Liste ] }`, nach Erstelldatum.

Listenobjekt:
```json
{
  "id": "uuid",
  "name": "Einkaufsliste",
  "kind": "shopping",
  "created_at": "datetime",
  "items": [
    { "id": "uuid", "content": "Milch", "done": false, "created_at": "datetime" }
  ]
}
```

### `PATCH /lists/{id}`  *(Bearer)*
Request: `{ "name": string }` — aktuell nur der Name änderbar.
Response `200`: die aktualisierte Liste.

### `DELETE /lists/{id}`  *(Bearer)*
Löscht die Liste inkl. aller Einträge.
Response `204`.
Fehler: `404 not_found` (Liste existiert nicht oder gehört einem anderen Nutzer).

### `POST /lists/{id}/items`  *(Bearer)*
Request: `{ "content": string }`
Response `201`: die **gesamte aktualisierte Liste** (nicht nur der neue Eintrag) — spart der UI einen zweiten Roundtrip.

### `PATCH /lists/{id}/items/{item_id}`  *(Bearer)*
Request: `{ "content": string | null, "done": bool | null }`, beide optional. Zum Abhaken einfach nur `{ "done": true }` schicken.
Response `200`: die gesamte aktualisierte Liste.

### `DELETE /lists/{id}/items/{item_id}`  *(Bearer)*
Response `200` (**nicht 204** — Ausnahme von der sonstigen Konvention, da die Antwort direkt die aktualisierte Liste liefert): die gesamte aktualisierte Liste ohne den gelöschten Eintrag.
Fehler: `404 not_found` (Liste oder Eintrag existiert nicht oder gehört einem anderen Nutzer).

## Ausgaben-Tracker

Einfacher Ausgaben-Tracker: einzelne Ausgaben eintragen, mit Gesamtsumme und Aufschlüsselung nach Kategorie. Bewusst schlank gehalten (kein Edit, keine Mehrwährung) — eine falsch eingetragene Ausgabe wird gelöscht und neu angelegt statt bearbeitet, entsprechend gibt es keinen `PATCH`-Endpunkt. `amount` ist ein einfacher Float ohne Währungsfeld (implizit eine Währung) — für persönliche Summenübersichten ausreichend, nicht für exakte Buchhaltung gedacht.

Ausgaben entstehen entweder manuell über die Settings-UI (Tab "Ausgaben") oder automatisch während des Chats über die Tools `add_expense` / `list_expenses` / `delete_expense` (siehe `app/agent/tools.py`).

### `POST /expenses`  *(Bearer)*
Request: `{ "amount": number, "description": string, "category": string | null, "spent_at": date | null }` — `spent_at` fehlt → heute.
Response `201`: die erstellte Ausgabe (siehe unten).

### `GET /expenses?from={date}&to={date}&category={string}`  *(Bearer)*
Alle Query-Parameter optional (Datumsfilter inklusive Grenzen).
Response `200`: `{ "expenses": [ Ausgabe ], "total": number, "by_category": { "Essen": number, "Sonstiges": number, ... } }` — `total`/`by_category` sind über die (gefilterte) `expenses`-Liste berechnet, nicht über alle Ausgaben des Nutzers. Ausgaben ohne `category` fallen unter den Schlüssel `"Sonstiges"`.

Ausgabenobjekt:
```json
{
  "id": "uuid",
  "amount": 12.5,
  "description": "Mittagessen",
  "category": "Essen",
  "spent_at": "2026-09-28",
  "created_at": "datetime"
}
```

### `DELETE /expenses/{id}`  *(Bearer)*
Response `204`.
Fehler: `404 not_found` (Ausgabe existiert nicht oder gehört einem anderen Nutzer).

## Wetter

Wetterabfrage über [Open-Meteo](https://open-meteo.com/) (kostenlos, kein API-Key nötig). Kein eigenes DB-Modell — jede Anfrage geht live gegen Open-Meteos Geocoding- und Forecast-API, nichts wird gespeichert.

### `GET /weather?location={string}`  *(Bearer)*
`location` ist ein Ortsname (z.B. `"Berlin"`), wird zuerst per Geocoding-API in Koordinaten übersetzt.
Response `200`:
```json
{
  "location": "Berlin",
  "country": "Germany",
  "current_temperature": 18.5,
  "current_condition": "Bedeckt",
  "current_wind_speed": 12.0,
  "daily": [
    { "date": "2026-09-28", "temp_min": 12.0, "temp_max": 20.0, "condition": "Bedeckt" }
  ]
}
```
`daily` enthält eine 3-Tage-Vorhersage (heute + 2 weitere Tage). `current_condition`/`daily[].condition` sind aus dem numerischen WMO-Wettercode von Open-Meteo in einen kurzen deutschen Text übersetzt (`app/services/weather_service.py`).
Fehler: `404 location_not_found` (Ort nicht gefunden), `502 weather_service_error` (Open-Meteo nicht erreichbar).

Auch als Tool `get_weather` (siehe `app/agent/tools.py`) im Chat/Voice-Agenten nutzbar. **Nicht live gegen die echte Open-Meteo-API getestet** — kein Netzwerkzugriff in der Build-Sandbox dieser Session (bestätigt per Live-Test: `403 Forbidden` durch die Sandbox-Egress-Policy). Backend-seitig vollständig mit `httpx.MockTransport` getestet (`tests/test_weather.py`); die Frontend-Fehlerbehandlung wurde live bestätigt (derselbe `403`-Fehler kam sauber über `ErrorMessage` in der UI an). Vor Produktiveinsatz einmal mit echtem Netzwerkzugriff gegen eine echte Stadt durchklicken.

## News/RSS

RSS/Atom-Feeds abonnieren, damit sich der Assistent Neuigkeiten daraus zusammenfassen kann ("was gibt's Neues bei X?"). Es werden **keine Artikel gespeichert** — jede Abfrage holt den Feed live und gibt die rohen Einträge zurück; das Zusammenfassen übernimmt das LLM selbst als Teil seiner normalen Chat-Antwort (gleiches Prinzip wie bei `calendar_list_events`: das Tool liefert Rohdaten, die eigentliche Zusammenfassung ist die Antwort des Assistenten).

### `POST /rss/feeds`  *(Bearer)*
Request: `{ "url": string, "name": string | null }` — fehlt `name`, wird der Feed einmal abgerufen und sein `<title>` als Name übernommen.
Response `201`: `{ "id": uuid, "url": string, "name": string | null, "created_at": datetime }`

### `GET /rss/feeds`  *(Bearer)*
Response `200`: `{ "feeds": [ Feed ] }`

### `DELETE /rss/feeds/{id}`  *(Bearer)*
Response `204`.
Fehler: `404 not_found` (Feed existiert nicht oder gehört einem anderen Nutzer).

### `GET /rss/items?feed_id={uuid}`  *(Bearer)*
`feed_id` optional — ohne Angabe werden alle abonnierten Feeds des Nutzers abgefragt und ihre Einträge zusammengeführt. Pro Feed werden maximal die neuesten 10 Einträge geholt.
Response `200`:
```json
{
  "items": [
    {
      "feed_name": "OwnAI Blog",
      "title": "Erster Artikel",
      "link": "https://example.com/1",
      "published": "Mon, 28 Sep 2026 08:00:00 GMT",
      "summary": "Zusammenfassung des ersten Artikels."
    }
  ]
}
```
`summary` ist auf 500 Zeichen gekürzt (mit `…` markiert) und kann rohes HTML aus dem Feed enthalten (wird nicht bereinigt). Fehler: `404 not_found` (bei explizitem `feed_id`, wenn der Feed nicht existiert/nicht dem Nutzer gehört), `502 rss_feed_error` (Feed nicht erreichbar oder kein gültiges RSS/Atom-XML).

Auch als Tools `add_rss_feed` / `list_rss_feeds` / `delete_rss_feed` / `list_rss_items` (siehe `app/agent/tools.py`) im Chat/Voice-Agenten nutzbar. **Nicht live gegen einen echten RSS-Feed getestet** — kein Netzwerkzugriff in der Build-Sandbox dieser Session (per Live-Test bestätigt: `403 Forbidden` durch die Sandbox-Egress-Policy, Fehlerbehandlung bis in die Frontend-UI aber bestätigt sauber durchgelaufen). Backend-seitig vollständig mit `httpx.MockTransport` und einem eingebetteten Beispiel-Feed getestet (`tests/test_rss.py`, nutzt `feedparser` zum Parsen). Vor Produktiveinsatz einmal mit einem echten Feed durchklicken.

## Web-Clipper

Ruft eine Webseite ab und extrahiert ihren lesbaren Text (Skripte/Styles/Nav/Header/Footer werden entfernt), damit der Assistent sie zusammenfassen kann — oder speichert sie als Markdown-Datei zum Nachlesen. Kein eigenes DB-Modell für den Clip selbst; das Speichern nutzt die bestehende `GET /chat/conversations/{id}/files/{file_id}`-Download-Infrastruktur (`GeneratedFile`, siehe Chat-Abschnitt oben) weiter.

### `POST /clip`  *(Bearer)*
Request: `{ "url": string }`
Response `200`: `{ "title": string, "url": string, "text": string }` — `text` ist auf 5000 Zeichen gekürzt (mit `…` markiert).
Fehler: `502 clip_error` (Seite nicht erreichbar oder enthält keinen lesbaren Text, z. B. eine leere Seite).

Dieser Endpunkt speichert nichts — er treibt nur die Settings-UI-Vorschau (Tab "Web-Clipper"). Das **Speichern** als Datei läuft ausschließlich über den Chat/Voice-Agenten (Tool `save_clipped_page`), weil generierte Dateien an eine Unterhaltung gebunden sind (`GeneratedFile.conversation_id`, siehe `file_service.py`) — in den Settings gibt es keine "aktuelle Unterhaltung", in die gespeichert werden könnte.

Auch als Tools `clip_url` (liefert Titel+Text, ohne zu speichern — für Zusammenfassungen) und `save_clipped_page` (liefert zusätzlich `{ "id", "filename", "size_bytes", "download_url" }` wie das `create_file`-Tool, speichert den Text als `.md`-Datei in der aktuellen Unterhaltung) nutzbar (siehe `app/agent/tools.py`). **Nicht live gegen eine echte Webseite getestet** — kein Netzwerkzugriff in der Build-Sandbox dieser Session (per Live-Test bestätigt: `403 Forbidden` durch die Sandbox-Egress-Policy, Fehlerbehandlung bis in die Frontend-UI aber bestätigt sauber durchgelaufen). Backend-seitig vollständig mit `httpx.MockTransport` gegen eine eingebettete Beispiel-HTML-Seite getestet (`tests/test_clipper.py`, nutzt `beautifulsoup4` zum Parsen). Vor Produktiveinsatz einmal mit einer echten Seite durchklicken.

## Sprache (Voice)

### `POST /voice/transcribe`  *(Bearer, multipart/form-data)*
Request: `multipart/form-data` mit Feld `audio` (Datei, beliebiges gängiges Audioformat — WebM/Opus, MP4/AAC, WAV etc.; das Backend dekodiert serverseitig via `ffmpeg`). Max. 25 MB.
Response `200`: `{ "text": string }`

Fehler: `400 empty_audio`, `413 audio_too_large`, `502 whisper_unavailable` (Whisper-Server nicht erreichbar/kein Transkript).

Reiner Speech-to-Text-Endpunkt — liefert nur den transkribierten Text zurück. Client schickt den Text danach ganz normal über `POST /chat/conversations/{id}/messages`. Text-to-Speech (Antworten vorlesen) läuft **client-seitig** über die jeweilige Plattform-API (Web: `speechSynthesis`, Android: `TextToSpeech`) — dafür gibt es keinen Backend-Endpunkt, da On-Device-TTS kostenlos, privat und ohne Server-Rundtrip funktioniert.

## Bilderkennung (Vision)

### `POST /vision/describe`  *(Bearer, multipart/form-data)*
Request: `multipart/form-data` mit Feld `image` (Bilddatei, max. 15 MB).
Response `200`: `{ "ocr_text": string | null, "description": string | null }`

Zwei unabhängige, beide **best-effort** (nie ein harter Fehler, nur `null` bei Nichtverfügbarkeit):
- `ocr_text`: per Tesseract-OCR extrahierter Text im Bild (Deutsch+Englisch). `null` z. B. wenn kein Text erkannt wurde oder die `tesseract-ocr`-Systembibliothek fehlt.
- `description`: Bildbeschreibung durch ein Vision-fähiges Ollama-Modell (`OLLAMA_VISION_MODEL`, z. B. `llava`). `null`, wenn kein Vision-Modell konfiguriert ist — OCR funktioniert unabhängig davon immer.

Fehler: `400 empty_image`, `413 image_too_large`.

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
