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

Vollständiger Code-Stand über alle vier Bausteine (Backend, Web, Android, iPad) gemäß `CONCEPT.md`/`DECISIONS.md`. Was in dieser Cloud-Session tatsächlich ausgeführt/getestet werden konnte vs. was du beim ersten eigenen Build noch verifizieren musst, steht am Ende der Session-Zusammenfassung bzw. in den jeweiligen `README.md` der Unterprojekte.
