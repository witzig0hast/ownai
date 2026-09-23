# OwnAI – Persönlicher KI-Assistent (Konzept)

Status: **Entwurf zur Abstimmung** – dient als Diskussionsgrundlage, bevor die Umsetzung geplant/priorisiert wird.

## 1. Zielbild

Ein vollständig selbst gehosteter, persönlicher KI-Assistent mit:

- Eigenen nativen/plattformübergreifenden Apps für **iPad**, **Android (S25 Ultra)** und **PC** (Web) – keine Drittanbieter-Chatplattformen (kein Telegram etc.)
- Eigenem Backend, eigener Authentifizierung/Anmeldung mit Zertifikaten
- Inferenz über **Ollama** auf einem Linux-Server mit **Nvidia Tesla P40 (24 GB VRAM)**, wobei bewusst **nicht das gesamte VRAM** ausgeschöpft wird (Puffer für parallele Modelle: Embeddings, STT, etc.)
- Werkzeugzugriff (Tool-/Function-Calling): Kalender, Benachrichtigungen/SMS auf dem Handy lesen und daraus Vorschläge generieren, später erweiterbar (Mail, Notizen, Smart Home, …)

## 2. Wichtiger Klärungsbedarf: „Hermes Agent" vs. „OpenClaw Agent"

Bevor ich mich hier festlege, eine Einordnung, damit wir vom Gleichen sprechen:

- **Hermes** ist mit hoher Wahrscheinlichkeit **Hermes 3 / Hermes 4** von NousResearch – das sind offene LLMs (kein Agent-Framework), die speziell auf starkes Tool-/Function-Calling und agentisches Verhalten trainiert sind. Laufen sehr gut über Ollama/GGUF. Das wäre also die **Modellwahl**, nicht die Orchestrierungsschicht.
- **„OpenClaw Agent"** ist mir als Begriff nicht klar zuordenbar (evtl. Verhören/Autokorrektur von z. B. „OpenHands", „Open Interpreter", „AutoGPT", „CrewAI" o. Ä.). Ich brauche hier eine Bestätigung, was gemeint war – **oder** wir entkoppeln bewusst:
  - **LLM** (das „Gehirn"): Hermes 3/4 via Ollama
  - **Agent-/Orchestrierungs-Schicht** (steuert Tool-Aufrufe, Gedächtnis, Multi-Step-Planung): eigene, schlanke Schicht auf Basis des **Model Context Protocol (MCP)** – das ist der offene Standard, über den auch Claude Code selbst Tools anspricht. Vorteil: Wir schreiben Kalender-/SMS-/Notiz-Tools einmal als MCP-Server und jedes LLM/Framework kann sie nutzen, unabhängig von einer Modewelle bei Agent-Frameworks.

**Empfehlung:** LLM und Agent-Framework getrennt betrachten, MCP als Tool-Standard nutzen. Bitte kurz bestätigen oder korrigieren.

## 3. Architektur-Überblick

```
┌─────────────────────────────────────────────────────────────────┐
│  Clients                                                          │
│  ┌───────────┐   ┌───────────────┐   ┌───────────────────────┐   │
│  │ iPad App  │   │ Android App   │   │ Web-App (PC)           │   │
│  │ (SwiftUI) │   │ (Kotlin,      │   │ (React/Next.js, PWA)   │   │
│  │           │   │  + Notif./SMS │   │                        │   │
│  │           │   │  Listener)    │   │                        │   │
│  └─────┬─────┘   └───────┬───────┘   └───────────┬────────────┘   │
└────────┼─────────────────┼────────────────────────┼───────────────┘
         │            HTTPS/WSS (mTLS oder OIDC+JWT über VPN)        
         ▼                 ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Linux-Server (Tesla P40, 24 GB VRAM)                             │
│                                                                     │
│  Reverse Proxy (Caddy/Traefik, TLS)                                │
│      │                                                             │
│  Auth-Dienst (Authentik/Keycloak – OIDC, Passkeys, mTLS optional)  │
│      │                                                             │
│  API-Gateway / Backend (FastAPI, Python)                          │
│      ├── Agent-Orchestrierung (Tool-Loop, Memory, Planung)         │
│      ├── MCP-Server: Kalender (CalDAV)                            │
│      ├── MCP-Server: Notifications/SMS-Analyse                    │
│      ├── MCP-Server: Notizen/Tasks (später: Mail, Home Assistant) │
│      ├── Postgres (Nutzer, Chats, Tasks, Kalender-Cache)           │
│      ├── pgvector/Qdrant (Langzeitgedächtnis, RAG)                 │
│      └── Redis (Sessions, Queues)                                  │
│                                                                     │
│  Ollama (GGUF-Modelle, quantisiert)                                │
│      ├── Hermes 3/4 8B–14B  (Haupt-Chat/Tool-Calling, ~14-18 GB)   │
│      ├── nomic-embed-text   (Embeddings, ~0,3 GB)                  │
│      └── optional: Whisper (STT) separat via faster-whisper        │
└─────────────────────────────────────────────────────────────────┘
```

### Wichtiger technischer Hinweis zur P40

Die Tesla P40 ist eine **Pascal-GPU ohne Tensor Cores** und mit schwacher FP16-Performance – sie ist für **FP32/INT8** ausgelegt. Für LLM-Inferenz heißt das konkret:

- **GGUF-Quantisierung (Q4_K_M / Q5_K_M) über llama.cpp/Ollama funktioniert gut** auf der P40 – das ist der Standardweg und genau das, was Ollama ohnehin nutzt.
- Native FP16/BF16-Backends (z. B. vLLM mit Standard-Settings) laufen auf der P40 **schlecht bis gar nicht performant** – daher ist Ollama (llama.cpp-basiert) hier die richtige Wahl, nicht vLLM/TGI.
- 24 GB VRAM reichen komfortabel für **8B–14B-Modelle in Q4/Q5/Q6**, ein 70B-Modell passt selbst stark quantisiert **nicht** rein (~40+ GB nötig). Empfehlung: Hermes 3/4 im 8B- oder 14B-Bereich als Hauptmodell.
- „Nicht komplett 24 GB nutzen": über Modellwahl (z. B. 8B/14B statt 32B/70B) und `OLLAMA_MAX_LOADED_MODELS`/`OLLAMA_KEEP_ALIVE` steuerbar, plus bewusst 6–8 GB Puffer für Embeddings/STT/parallele Anfragen freihalten.

## 4. Wichtige Plattform-Einschränkung: SMS/Benachrichtigungen lesen

Das ist technisch **nur auf Android möglich**, nicht auf iOS/iPadOS:

- **Android**: Über einen `NotificationListenerService` (+ ggf. SMS-Permission) kann eine eigene App Benachrichtigungen/SMS mitlesen und sicher an das Backend weiterleiten. Das ist Standard-Android-API, erfordert aber explizite Nutzerfreigabe (Sonderberechtigung).
- **iOS/iPadOS**: Apple erlaubt **keinen** Zugriff einer App auf Benachrichtigungen/SMS anderer Apps (Sandboxing). Es gibt keine offizielle API dafür – auch nicht für eigene Apps. Optionen wären nur Krücken (Kurzbefehle/Shortcuts-Automationen, die der Nutzer manuell einrichtet, Share-Sheet-Erweiterungen) – kein automatisches „stilles" Mitlesen.

Das passt aber gut zur genannten Geräteaufteilung: Das **S25 Ultra (Android)** ist ohnehin das SMS/Benachrichtigungs-Quellgerät, iPad/PC sind reine Zugriffs-/Anzeige-Clients für den Assistenten. Kein Widerspruch, nur zur Klarheit festgehalten.

## 5. Client-Strategie

Empfehlung: **native Apps pro Plattform**, um vollen Zugriff auf OS-Integrationen zu haben (Kalender, Notification Listener, Shortcuts/Widgets), verbunden über ein gemeinsames Backend/API:

| Plattform | Technologie | Begründung |
|---|---|---|
| Android (S25 Ultra) | Kotlin, Jetpack Compose | Voller Zugriff auf `NotificationListenerService`, SMS, Widgets, Hintergrunddienste |
| iPad | Swift/SwiftUI | Beste Integration in Kalender/Reminders/Shortcuts, native Performance |
| PC | Web-App (Next.js/React, PWA, offline-fähig) | Plattformunabhängig, kein Electron-Overhead, per Browser/PWA auf jedem PC nutzbar |

Alternative wäre ein Cross-Platform-Framework (Flutter/React Native) für schnellere Entwicklung mit einer Codebasis, dafür mit Native-Modulen für die Android-Notification-Integration. **Trade-off, den wir gemeinsam entscheiden sollten** (siehe offene Fragen).

## 6. Backend-Bausteine

- **API-Gateway**: FastAPI (Python) – passt gut zu Ollama/ML-Ökosystem, einfache Anbindung an MCP-Server (auch in Python)
- **Agent-Orchestrierung**: eigener Tool-Loop gegen Ollamas OpenAI-kompatible API, Tools über MCP angebunden
- **Datenhaltung**: Postgres (strukturierte Daten), pgvector oder Qdrant (Langzeitgedächtnis/RAG), Redis (Sessions/Queues)
- **Auth**: Authentik oder Keycloak (OIDC), **Passkeys/WebAuthn** als primärer Login (zertifikatsbasiert, phishing-resistent) + optional mTLS zwischen Apps und API für zusätzliche Absicherung
- **Netzwerk**: Empfehlung **Tailscale/WireGuard-Mesh** statt öffentlicher Exposition – Apps verbinden sich nur über privates VPN mit dem Server (deutlich kleinere Angriffsfläche für ein System, das SMS-Inhalte verarbeitet). Alternative: öffentlicher Domain-Zugang mit hartem Hardening – **Entscheidung offen**.
- **Deployment**: Docker Compose auf dem Linux-Server, ein Service je Baustein (ollama, api, mcp-*, postgres, redis, caddy, authentik)

## 7. Tools/Integrationen – Reihenfolge

**Welle 1 (MVP-Werkzeuge):**
1. Kalender (CalDAV – kompatibel zu Apple Calendar, Google Calendar, Nextcloud)
2. Android-Benachrichtigungs-/SMS-Analyse inkl. Vorschlagsgenerierung („Antwortvorschlag", „Termin erkannt → ins Kalender übernehmen?")

**Welle 2:**
3. Notizen/Tasks (eigene oder Anbindung an bestehende, z. B. Nextcloud)
4. Mail (IMAP, lesend + Entwurfsvorschläge)

**Welle 3:**
5. Smart Home (Home Assistant), Web-Suche, Sprachein-/ausgabe (Whisper STT + TTS)

## 8. Sicherheit & Datenschutz

Da SMS-/Benachrichtigungsinhalte hochsensibel sind:

- Ausschließlich Verarbeitung auf dem eigenen Server, **keine Cloud-LLM-Calls** (bewusste Grundentscheidung, passend zum Self-Hosting-Wunsch)
- Transportverschlüsselung überall (TLS/mTLS), Zugriff nur über VPN-Mesh oder gehärteten Reverse Proxy
- Verschlüsselung sensibler Felder at-rest (z. B. Nachrichteninhalte in Postgres)
- Audit-Log für Tool-Aufrufe des Agenten (Nachvollziehbarkeit: was hat der Assistent wann gelesen/ausgeführt)
- Klare Berechtigungs-/Zustimmungsschritte in der Android-App für den Notification-Zugriff

## 9. Phasenplan

| Phase | Inhalt |
|---|---|
| 0 | Server-Setup: Docker, Ollama + Hermes-Modell, Reverse Proxy, Auth-Grundgerüst |
| 1 | Backend-Kern: Chat-API gegen Ollama, Nutzerverwaltung, einfache Web-App |
| 2 | Mobile MVP: Android- und iPad-App mit Chat-UI, Login, Push |
| 3 | Kalender-Tool-Integration (MCP-Server + Agent-Anbindung) |
| 4 | Android Notification/SMS-Listener + Vorschlagslogik |
| 5 | Langzeitgedächtnis/RAG, weitere Tools (Mail, Notizen) |
| 6 | Sprachsteuerung, Widgets, proaktive Vorschläge, Feinschliff |

## 10. Offene Fragen an dich

1. **„OpenClaw Agent"** – was genau war gemeint? Oder passt die Entkopplung „Hermes als Modell + MCP-basierte eigene Orchestrierung" für dich?
2. **Netzwerkzugriff**: VPN-only (Tailscale/WireGuard) oder öffentlich erreichbar mit eigener Domain?
3. **Client-Technologie**: native Apps pro Plattform (Swift/Kotlin/Web) oder ein Cross-Platform-Framework (Flutter/React Native) für schnellere Entwicklung?
4. **Apple Developer Program** (99 $/Jahr) vorhanden/gewünscht für App-Store/TestFlight, oder reicht Sideloading/eigenes Signing fürs iPad?
5. **Sprachsteuerung** (STT/TTS) schon für v1 relevant oder erstmal Text-only?
6. Grobe **Zeit-/Ressourcenerwartung** – soll das schrittweise über mehrere Sessions entstehen (empfohlen, da sehr umfangreich), oder gibt es einen Teilbereich, den du zuerst sehen willst (z. B. erstmal nur Backend + Web-Chat als Fundament)?

---

Sobald die offenen Punkte geklärt sind, lege ich als nächsten Schritt das Repo-Grundgerüst an (Backend-Skeleton, Docker-Compose für Ollama+Postgres, erste MCP-Server-Struktur) und wir arbeiten uns Phase für Phase vor.
