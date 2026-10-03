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

## Status dieses Durchgangs

Vollständiger Code-Stand über alle vier Bausteine (Backend, Web, Android, iPad) gemäß `CONCEPT.md`/`DECISIONS.md`.

| Baustein | In dieser Session verifiziert | Noch zu tun bei dir |
|---|---|---|
| `backend/` | 15 Tests grün (Auth, Chat/Tool-Loop, Kalender, Notifications, gemockt), `ruff` sauber, echter `alembic upgrade head`-Lauf, App bootet und beantwortet `/health` | Einmal gegen echtes Ollama + echten CalDAV-Account testen |
| `web/` | `npm run build` + `npm run lint` grün, dabei einen echten `docker-compose`-Bug gefunden/gefixt | `docker compose build web` einmal auf deiner Maschine (kein Docker-Daemon hier verfügbar) |
| `mobile/android/` | Alle 41 Kotlin-Dateien klammerbalanciert, Paketdeklarationen geprüft, Gradle-Wrapper ist eine echte Gradle-8.9-Distribution, Abhängigkeits-IDs gegen Maven Central geprüft (soweit erreichbar) | Einmal in Android Studio öffnen und bauen (kein Android SDK hier verfügbar); `dl.google.com` war vom Netzwerk-Proxy dieser Session blockiert, d.h. die Google-Maven-Versionspins (Compose BOM, androidx.security etc.) sind plausibel, aber nicht live gegen das Repository verifiziert |
| `mobile/ios/` | Alle Swift-Dateien klammerbalanciert, `project.yml` als YAML validiert, zwei echte Bugs beim Review gefunden und gefixt (nicht-optionaler `title`, großgeschriebene UUIDs in URL-Pfaden) | Einmal `xcodegen generate` + Xcode-Build (kein Xcode/Swift-Toolchain hier verfügbar) |

Details und bewusste Scope-Cuts stehen jeweils in `backend/README.md`, `web/README.md`, `mobile/android/README.md`, `mobile/ios/README.md`.
