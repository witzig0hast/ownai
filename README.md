# OwnAI

Persönlicher, selbst gehosteter KI-Assistent: eigenes Backend, eigene Apps (iPad, Android, Web), Inferenz über Ollama auf einer Nvidia Tesla P40.

**Lies zuerst:**
1. [`CONCEPT.md`](./CONCEPT.md) — Architektur, Begründungen, Trade-offs
2. [`DECISIONS.md`](./DECISIONS.md) — getroffene Entscheidungen zu den offenen Fragen aus dem Konzept
3. [`API.md`](./API.md) — verbindlicher Schnittstellenvertrag zwischen Backend und den drei Clients

## Struktur

```
ownai/
├── backend/            FastAPI-Backend (Auth, Chat/Agent-Loop, Kalender, Notifications)
├── web/                Next.js Web-App (PC-Client)
├── mobile/
│   ├── android/        Kotlin/Compose App (S25 Ultra) inkl. Notification-Listener
│   └── ios/             SwiftUI App (iPad)
├── infra/
│   ├── caddy/          Reverse-Proxy-Config (TLS)
│   └── ollama/          Ollama-Setup-Doku für die P40
├── docker-compose.yml   Orchestriert ollama, postgres, redis, backend, web, caddy
└── .env.example
```

## Schnellstart (Server)

```bash
cp .env.example .env
# .env ausfüllen: SECRET_KEY, POSTGRES_PASSWORD, DOMAIN

docker compose up -d postgres redis ollama
docker exec -it ownai-ollama ollama pull hermes3:8b
docker exec -it ownai-ollama ollama pull nomic-embed-text

docker compose up -d backend web caddy
```

Details zur GPU/Modellwahl: [`infra/ollama/README.md`](./infra/ollama/README.md).
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
