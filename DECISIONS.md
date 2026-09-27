# Entscheidungen (v1)

Du hast gesagt: „Bau das alles voll aus." Damit das nicht an offenen Fragen aus `CONCEPT.md` (Abschnitt 10) hängen bleibt, habe ich sie mit begründeten Standardentscheidungen aufgelöst. Alles hier ist **änderbar** — einfach sagen, was anders sein soll.

| # | Frage | Entscheidung | Begründung |
|---|---|---|---|
| 1 | „Hermes" vs. „OpenClaw Agent" | **Hermes 3 als LLM** (`hermes3:8b` als Default, austauschbar), **eigene MCP-basierte Orchestrierung** statt eines externen Agent-Frameworks | Kein Drittanbieter-Agent-Framework nötig, volle Kontrolle, Tools über den offenen MCP-Standard nutzbar (auch von anderen MCP-Clients wie Claude Desktop) |
| 2 | Netzwerkzugriff | Backend/Reverse Proxy **netzwerk-agnostisch gebaut** (TLS via Caddy), als **Default-Empfehlung: Tailscale-VPN-Mesh**, in `docker-compose.yml`/README dokumentiert, aber nicht hart verdrahtet | Geringste Angriffsfläche für ein System, das SMS-Inhalte verarbeitet; du kannst trotzdem später öffentlich exponieren, wenn gewünscht |
| 3 | Client-Technologie | **Nativ pro Plattform**: Kotlin/Compose (Android), Next.js/React PWA (Web + iPad) | Notwendig für tiefe OS-Integration auf Android (NotificationListenerService); für iPad/PC siehe #4/#7 — kein natives SwiftUI mehr als aktiver Pfad |
| 4 | Apple Developer Account | **Nicht nötig** — keine Veröffentlichung, keine native iPad-App als aktiver Pfad (siehe #7) | Entfällt durch #7 |
| 5 | Sprachsteuerung (STT/TTS) | **Nicht in diesem Durchgang** (bleibt Phase 6 in `CONCEPT.md`) | Fokus zuerst auf Kernsystem: Chat, Kalender, Notifications |
| 6 | Umfang dieses Durchgangs | **Alle vier Bausteine gleichzeitig**: Backend, Web, Android, iPad — als solides, durchgängiges Grundgerüst mit den MVP-Kernfunktionen aus Welle 1 (Chat, Auth, Kalender, Android-Notification-Analyse) | Entspricht „bau das alles voll aus" |
| 7 | iPad-App: nativ (SwiftUI) vs. Web/PWA | **Web-App als PWA** (installierbar über Safari „Zum Home-Bildschirm", eigenes Icon, Vollbild-Modus) ist der aktive Pfad für iPad **und** PC. Der SwiftUI-Code in `mobile/ios/` bleibt vollständig im Repo, ist aber **nicht der aktive Pfad** | Du hast nur einen Windows-PC — Xcode läuft ausschließlich auf macOS, du hast also aktuell keine Möglichkeit, die native App selbst zu bauen. Die PWA braucht keinen Mac und keinen Apple-Developer-Account |
| 8 | Vertrieb / Veröffentlichung | **Explizit keine Veröffentlichung** — reiner Eigenbedarf auf deinen eigenen Geräten (Windows-PC, iPad, S25 Ultra) | Deine Vorgabe. Android: Sideload per `adb install` oder APK-Transfer, kein Play Store, keine Play-Signing-Konfiguration nötig. Web/PWA: läuft direkt vom eigenen Server, kein App Store nötig |

## Wichtige Einschränkung dieses Durchgangs (Transparenz)

Diese Session läuft in einem Linux-Cloud-Container **ohne** Xcode/Swift-Toolchain und **ohne** Android SDK/laufenden Docker-Daemon. Das heißt konkret:

- **Backend** (Python/FastAPI): wird von mir tatsächlich lokal ausgeführt, mit Tests gegen SQLite verifiziert (Postgres-Schema bleibt kompatibel, siehe `backend/README.md`).
- **Web-App** (Next.js, PWA — aktiver Client für PC **und** iPad): Build/Lint wird tatsächlich ausgeführt, Manifest/Icons/Install-Metadaten wurden gegen eine laufende Instanz verifiziert.
- **Android-App** (Kotlin/Compose): Quellcode wird vollständig und sorgfältig geschrieben, kann in diesem Container aber **nicht kompiliert** werden (kein Android SDK). Du musst sie einmal in Android Studio öffnen, bauen und per `adb install` auf dein S25 Ultra bringen (kein Play Store nötig, siehe Entscheidung #8).
- **iPad-App** (SwiftUI, `mobile/ios/`): Quellcode ist vollständig und wurde beim Review verifiziert, ist aber laut Entscheidung #7 **nicht der aktive Pfad** (kein Mac vorhanden) — bleibt für später im Repo liegen, falls sich das ändert.

Ich kennzeichne das im finalen Report noch einmal klar, damit hier keine falschen Erwartungen entstehen — „voll ausgebaut" heißt also: vollständiger, in sich konsistenter Code entlang des gesamten Konzepts, mit ehrlicher Kennzeichnung, was ich in dieser Umgebung selbst verifizieren konnte und was du beim ersten Build auf deiner Seite noch prüfen musst.
