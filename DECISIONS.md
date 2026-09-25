# Entscheidungen (v1)

Du hast gesagt: „Bau das alles voll aus." Damit das nicht an offenen Fragen aus `CONCEPT.md` (Abschnitt 10) hängen bleibt, habe ich sie mit begründeten Standardentscheidungen aufgelöst. Alles hier ist **änderbar** — einfach sagen, was anders sein soll.

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| 1 | „Hermes" vs. „OpenClaw Agent" | **Hermes 3 als LLM** (`hermes3:8b` als Default, austauschbar), **eigene MCP-basierte Orchestrierung** statt eines externen Agent-Frameworks | Kein Drittanbieter-Agent-Framework nötig, volle Kontrolle, Tools über den offenen MCP-Standard nutzbar (auch von anderen MCP-Clients wie Claude Desktop) |
| 2 | Netzwerkzugriff | Backend/Reverse Proxy **netzwerk-agnostisch gebaut** (TLS via Caddy), als **Default-Empfehlung: Tailscale-VPN-Mesh**, in `docker-compose.yml`/README dokumentiert, aber nicht hart verdrahtet | Geringste Angriffsfläche für ein System, das SMS-Inhalte verarbeitet; du kannst trotzdem später öffentlich exponieren, wenn gewünscht |
| 3 | Client-Technologie | **Nativ pro Plattform**: Kotlin/Compose (Android), SwiftUI (iPad), Next.js/React PWA (Web) | Notwendig für tiefe OS-Integration (NotificationListenerService, EventKit) |
| 4 | Apple Developer Account | Angenommen: **noch nicht vorhanden**. iOS-App wird für lokalen Xcode-Build/TestFlight vorbereitet; App-Store-Submission ist ein späterer, unabhängiger Schritt | Blockiert die Entwicklung nicht |
| 5 | Sprachsteuerung (STT/TTS) | **Nicht in diesem Durchgang** (bleibt Phase 6 in `CONCEPT.md`) | Fokus zuerst auf Kernsystem: Chat, Kalender, Notifications |
| 6 | Umfang dieses Durchgangs | **Alle vier Bausteine gleichzeitig**: Backend, Web, Android, iPad — als solides, durchgängiges Grundgerüst mit den MVP-Kernfunktionen aus Welle 1 (Chat, Auth, Kalender, Android-Notification-Analyse) | Entspricht „bau das alles voll aus" |

## Wichtige Einschränkung dieses Durchgangs (Transparenz)

Diese Session läuft in einem Linux-Cloud-Container **ohne** Xcode/Swift-Toolchain und **ohne** Android SDK/laufenden Docker-Daemon. Das heißt konkret:

- **Backend** (Python/FastAPI): wird von mir tatsächlich lokal ausgeführt, mit Tests gegen SQLite verifiziert (Postgres-Schema bleibt kompatibel, siehe `backend/README.md`).
- **Web-App** (Next.js): Build/Lint wird tatsächlich ausgeführt.
- **Android-App** (Kotlin/Compose): Quellcode wird vollständig und sorgfältig geschrieben, kann in diesem Container aber **nicht kompiliert** werden (kein Android SDK). Du musst sie einmal in Android Studio öffnen und bauen.
- **iPad-App** (SwiftUI): Quellcode wird vollständig geschrieben, kann in diesem Container aber **nicht kompiliert** werden (kein macOS/Xcode). Du musst sie einmal in Xcode öffnen und bauen.

Ich kennzeichne das im finalen Report noch einmal klar, damit hier keine falschen Erwartungen entstehen — „voll ausgebaut" heißt also: vollständiger, in sich konsistenter Code entlang des gesamten Konzepts, mit ehrlicher Kennzeichnung, was ich in dieser Umgebung selbst verifizieren konnte und was du beim ersten Build auf deiner Seite noch prüfen musst.
