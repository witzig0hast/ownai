# OwnAI

Persönlicher, selbst gehosteter KI-Assistent: eigenes Backend, eigene Apps (iPad, Android, Web), Inferenz über Ollama auf einer Nvidia Tesla P40.

**Lies zuerst:**
1. [`GETTING_STARTED.md`](./GETTING_STARTED.md) — konkrete Schritt-für-Schritt-Anleitung, um alles zum Laufen zu bringen
2. [`CONCEPT.md`](./CONCEPT.md) — Architektur, Begründungen, Trade-offs
3. [`DECISIONS.md`](./DECISIONS.md) — getroffene Entscheidungen zu den offenen Fragen aus dem Konzept
4. [`API.md`](./API.md) — verbindlicher Schnittstellenvertrag zwischen Backend und den drei Clients

## Struktur

```
ownai/
├── backend/            FastAPI-Backend (Auth, Chat/Agent-Loop, Kalender, Notifications)
├── web/                Next.js Web-App (PC-Client)
├── mobile/
│   ├── android/        Kotlin/Compose App (S25 Ultra) inkl. Notification-Listener
│   └── ios/             SwiftUI App (iPad)
├── infra/
│   ├── caddy/          Reverse-Proxy-Config (TLS) — optional, siehe unten
│   ├── ollama/          Ollama-Setup-Doku für die P40
│   ├── kokoro/          Setup-Doku für den optionalen neuralen TTS-Server
│   └── searxng/         Setup-Doku für die optionale eigene SearXNG-Instanz (Web-Suche)
├── scripts/            backup.sh / restore.sh (Datenbank, erzeugte Dateien, .env)
├── docker-compose.yml   Orchestriert postgres, redis, backend, web (+ optional caddy) —
│                        Ollama läuft separat auf deinem Server, siehe infra/ollama/README.md
└── .env.example
```

## Schnellstart (Server)

Setzt eine eigene, bereits laufende Ollama-Instanz auf dem Server voraus (siehe [`infra/ollama/README.md`](./infra/ollama/README.md), falls noch nicht vorhanden):

```bash
ollama pull hermes3:8b
ollama pull nomic-embed-text

cp .env.example .env
# .env ausfüllen: SECRET_KEY, POSTGRES_PASSWORD, DOMAIN

docker compose up -d
```

Das startet standardmäßig **kein** Caddy — nur postgres, redis, backend, web (Caddy ist als
Compose-Profil `caddy` markiert und bindet sonst ungefragt :80/:443, was mit einem bereits
laufenden eigenen Reverse Proxy kollidiert).

- **Hast du schon einen eigenen Reverse Proxy** (Nginx, Apache, Traefik, ...)? Dann brauchst du
  Caddy nicht — richte dort einen Server-Block ein, der `/api/*` an `backend:8000` und alles
  andere an `web:3000` weiterleitet (die exakte Routing-Logik steht zum Abgleich in
  [`infra/caddy/Caddyfile`](./infra/caddy/Caddyfile)), inklusive TLS-Terminierung dort.
  **Wichtig bei Nginx**: der Standard-`proxy_read_timeout` (meist 60s) ist für eine lokale LLM-Antwort
  oft zu kurz, besonders bei langen Unterhaltungen oder Werkzeug-Aufrufen — zu knapp eingestellt
  äußert sich das als `504 Gateway Timeout` im Chat, obwohl das Backend selbst noch arbeitet. Setze
  `proxy_read_timeout 300s;` (und `proxy_connect_timeout 300s;`) im `location /api/`-Block.
- **Hast du noch keinen eigenen Reverse Proxy?** Dann starte Caddy zusätzlich mit:
  ```bash
  docker compose --profile caddy up -d
  ```
  Caddy übernimmt dann automatisch TLS (Let's Encrypt) für `DOMAIN` aus deiner `.env`.

Details zur GPU/Modellwahl und wie OwnAI deine Ollama-Instanz erreicht: [`infra/ollama/README.md`](./infra/ollama/README.md).
Backend-Entwicklung/Tests lokal ohne Docker: [`backend/README.md`](./backend/README.md).

## Was drin ist

- **Übersicht** als Startseite: Termine heute, Wetter, Listen zum Abhaken, Erinnerungen, Geburtstage, Monatsausgaben; **Morgen-Briefing** zum Vorlesen oder täglich als Push
- **Sprechen** (Live Talk, freihändig, mit antippbaren Vorschlägen) und **Chat** (Text, Bilder, Spracheingabe) mit drei Modi (Allgemein, Zuhause, Organisation)
- **Suche über alles** (Unterhaltungen, Gedächtnis, Kontakte, Listen, Erinnerungen, Ausgaben) und **Teilen an OwnAI** aus anderen Apps (Android, Chrome/Edge am PC)
- Werkzeuge für Kalender (CalDAV), Home Assistant, Timer, Erinnerungen, Listen, Ausgaben, Kontakte, Wetter, Web-Suche (SearXNG), RSS, Dateien, E-Mail
- **Gedächtnis** über Unterhaltungen hinweg, **Automatisierungen** (Home-Assistant-Regeln), dauerhafte **Agenten**, **Agent Bus** für externe Programme
- **Eingehende E-Mails** mit Bestätigungspflicht für alles mit Folgen
- Mehrbenutzer mit Admin-Freischaltung, optional **SSO** (beliebiger OIDC-Provider, z.B. Authentik), Login-Sperre gegen Passwort-Raten
- Web-Push, Einrichtungs-Checkliste für neue Nutzer, Hilfe-Seite in der App, Leiste unten am Handy, Dunkelmodus-Schalter, Ausgaben-Diagramm
- Admin: Registrierung/Freischaltung, System-Pause, **Systemstatus** aller Abhängigkeiten
- Betrieb: `scripts/backup.sh` / `scripts/restore.sh`, Logs-Tab für Nutzer

## Backups

```bash
scripts/backup.sh /mnt/nas/ownai     # Datenbank + erzeugte Dateien + .env, behält die 14 neuesten
scripts/restore.sh /mnt/nas/ownai/<zeitstempel>
```

Details und Cronjob-Beispiel: [`GETTING_STARTED.md`](./GETTING_STARTED.md#9-backups-einrichten). Die `.env` gehört zwingend ins Backup — gespeicherte Zugangsdaten sind mit einem aus `SECRET_KEY` abgeleiteten Schlüssel verschlüsselt.

## Stand

| Baustein | Stand | Verifiziert |
|---|---|---|
| `backend/` | Voll ausgebaut, aktiv genutzt | 284 Tests grün, `ruff` sauber, Migrationen gegen frische DB geprüft, live gegen echtes Ollama/Authentik betrieben |
| `web/` (PWA, auch fürs iPad) | Voll ausgebaut, **primärer Client** | `npm run build` + `lint` + `tsc` grün, live im Einsatz |
| `mobile/android/` | Grundfunktionen: Chat, Kalender, Sprache, Timer-Alarme, Benachrichtigungs-Weiterleitung für „Vorschläge" | Seit den frühen Ausbaustufen nicht mitgezogen — SSO, Bestätigungen, Gedächtnis, Listen, Agenten usw. gibt es nur im Web. Für alles darüber hinaus die Web-App als PWA auf dem Handy installieren. In dieser Umgebung nie kompiliert (kein Android SDK) |
| `mobile/ios/` | Eingefroren (siehe `DECISIONS.md` #7) | Das iPad nutzt die Web-App als PWA |

Details und bewusste Scope-Cuts stehen jeweils in `backend/README.md`, `web/README.md`, `mobile/android/README.md`, `mobile/ios/README.md`.
