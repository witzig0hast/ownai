# Los geht's – Schritt-für-Schritt-Anleitung

Konkrete Checkliste, um OwnAI von hier aus zum Laufen zu bringen. Reihenfolge einhalten — jeder Schritt baut auf dem vorherigen auf. Verweise auf ausführlichere Doku sind verlinkt, hier steht nur, was du tatsächlich tippen musst.

## 1. Server vorbereiten (Linux-Maschine mit der Tesla P40)

Da du schon eine laufende Ollama-Instanz hast, braucht OwnAI selbst **keinen** GPU-Zugriff von Docker aus — nur Docker + Compose für Backend/Web/Postgres/Redis/Caddy:

```bash
curl -fsSL https://get.docker.com | sh
```

(Das Nvidia Container Toolkit brauchst du nur, falls deine Ollama-Instanz selbst in Docker läuft und noch keinen GPU-Zugriff hat — dann hast du das aber vermutlich schon eingerichtet, sonst würde sie nicht auf der P40 laufen.)

## 2. Repo klonen und konfigurieren

```bash
git clone https://github.com/witzig0hast/ownai.git
cd ownai
git checkout claude/friendly-hypatia-1ght8l   # oder main, falls du den Branch gemerged hast

cp .env.example .env
```

`.env` öffnen und ausfüllen:
- `SECRET_KEY`: generieren mit `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `POSTGRES_PASSWORD`: ein beliebiges starkes Passwort
- `DOMAIN`: fürs Erste reicht `localhost` oder die IP deines Servers im lokalen Netz — echte Domain erst bei Schritt 6 nötig

## 3. Backend starten (nutzt deine vorhandene Ollama-Instanz)

Da du schon Ollama auf dem Server laufen hast: einfach das nötige Modell dort pullen (falls noch nicht vorhanden) und `OLLAMA_BASE_URL` in `.env` unangetastet lassen — der Default `http://host.docker.internal:11434` erreicht deine bestehende Instanz automatisch:

```bash
ollama pull hermes3:8b
ollama pull nomic-embed-text

# Kurzer Check: lauscht dein Ollama auf mehr als nur 127.0.0.1?
# (nötig, damit der Docker-Container vom Host aus rankommt — Details und Fix
#  falls nicht: infra/ollama/README.md, "Eigene Ollama-Instanz einrichten")
curl http://localhost:11434/api/tags

docker compose up -d postgres redis
docker compose up -d backend
```

Prüfen, dass alles läuft:

```bash
curl http://localhost:8000/api/v1/health
# erwartete Antwort: {"status":"ok","ollama":"ok"}
```

Steht `"ollama":"unreachable"` da: `docker compose logs ollama` checken, meist braucht das erste Modell-Laden noch ein paar Sekunden — kurz erneut versuchen.

Details/Hintergrund zur Modellwahl und VRAM-Begrenzung: [`infra/ollama/README.md`](./infra/ollama/README.md).

## 4. Web-App starten und im Browser testen

```bash
docker compose up -d web caddy
```

Im Browser auf dem Server (oder per SSH-Portweiterleitung `ssh -L 3000:localhost:3000 user@server`): `http://localhost:3000` öffnen, registrieren, einloggen, eine Chat-Nachricht schicken. Das ist der erste echte End-to-End-Test des ganzen Systems.

Falls etwas schiefgeht: `docker compose logs backend` bzw. `docker compose logs web`.

## 5. Kalender verbinden (optional, aber empfohlen zum Testen)

In der Web-App unter „Calendar" → „Connect CalDAV" deine echten Zugangsdaten eintragen (Apple/Google/Nextcloud-CalDAV-URL). Danach im Chat z. B. fragen: „Habe ich heute noch was vor?" — das testet den kompletten Tool-Calling-Pfad (LLM → Kalender-Tool → Antwort).

## 6. Netzwerkzugriff für deine Geräte einrichten

Empfehlung aus `DECISIONS.md`: **Tailscale**, damit iPad/PC/Handy den Server erreichen, ohne ihn öffentlich ins Internet zu stellen.

```bash
# auf dem Server:
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Dann Tailscale auch auf iPad, Windows-PC und S25 Ultra installieren (App Store / Microsoft Store / Play Store — das ist keine „eigene App", sondern ein Standard-VPN-Client) und alle im selben Tailnet einloggen. Der Server ist danach unter seinem Tailscale-Hostnamen erreichbar, z. B. `http://ownai-server:3000`.

Sobald das steht: `DOMAIN` in `.env` auf den Tailscale-Hostnamen setzen und `docker compose up -d --build web caddy` erneut laufen lassen (Web-App muss neu gebaut werden, siehe `web/README.md`, „NEXT_PUBLIC_API_BASE_URL gotcha").

## 7. Web-App als „App" auf iPad und PC installieren

- **iPad**: Safari öffnen, zur `DOMAIN`-URL navigieren, Teilen-Button → „Zum Home-Bildschirm". Läuft danach im Vollbild mit eigenem Icon.
- **Windows-PC**: Edge oder Chrome öffnen, zur URL navigieren, Install-Icon in der Adressleiste klicken (oder Menü → „Apps" → „OwnAI installieren").

## 8. Android-App bauen und aufs S25 Ultra bringen

Auf einem PC mit [Android Studio](https://developer.android.com/studio):

```bash
cd mobile/android
```

Projekt in Android Studio öffnen (Gradle synct automatisch). Dann:

```bash
./gradlew assembleDebug -PownaiApiBaseUrl="http://ownai-server:8000/api/v1/"
```

(URL an deine echte Tailscale-Adresse aus Schritt 6 anpassen, **Slash am Ende nicht vergessen**.)

APK liegt danach unter `app/build/outputs/apk/debug/app-debug.apk`. Aufs Handy:

```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

(USB-Debugging vorher aktivieren: Einstellungen → Über das Telefon → 7x auf „Build-Nummer" tippen → Entwickleroptionen → USB-Debugging.)

App öffnen, einloggen, dann **„Notification access" gewähren**, wenn die App danach fragt — ohne diese Berechtigung liest sie keine Benachrichtigungen. Danach: eine WhatsApp-Nachricht mit einer Zeitangabe schicken lassen, kurz warten, in der Web-App unter „Suggestions" nachschauen, ob ein Terminvorschlag auftaucht — das testet den kompletten Notification-Pfad.

Details: [`mobile/android/README.md`](./mobile/android/README.md).

---

## Kurz-Checkliste zum Abhaken

- [ ] Docker + Docker Compose auf dem Server (Nvidia Container Toolkit nur nötig, falls du Schritt 1 für eine *neue* GPU-Nutzung durchgehst — deine bestehende Ollama-Instanz hat das vermutlich schon)
- [ ] `.env` ausgefüllt
- [ ] Modelle auf deiner bestehenden Ollama-Instanz gepullt, `curl localhost:11434/api/tags` erreichbar
- [ ] `docker compose up -d postgres redis backend web caddy`, `/health` zeigt `"ollama":"ok"`
- [ ] Web-App im Browser getestet (Registrierung, Chat)
- [ ] CalDAV verbunden, Kalender-Tool im Chat getestet
- [ ] Tailscale auf Server + allen Geräten
- [ ] Web-App auf iPad und PC als App installiert
- [ ] Android-App gebaut, per `adb install` aufs S25 Ultra, Notification-Zugriff gewährt, ein Vorschlag erfolgreich erzeugt

Wenn du an einem Punkt hängen bleibst: einfach den Fehler/die Ausgabe hier reinkopieren, dann schauen wir's uns zusammen an.
