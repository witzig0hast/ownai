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
- `BACKEND_PORT`/`WEB_PORT`: Standard `8000`/`3000`. Belegt auf deinem Server (du hast ja schon andere Dienste laufen)? Erst prüfen: `ss -tlnp | awk '{print $4}' | grep -oE '[0-9]+$' | sort -n -u`, dann hier auf freie Ports ändern. In den restlichen Anleitungsschritten unten `8000`/`3000` gedanklich durch deine gewählten Ports ersetzen.
- Greifst du direkt per IP:Port zu (ohne Caddy/Domain, siehe Schritt 6): zusätzlich `NEXT_PUBLIC_API_BASE_URL` (z.B. `http://192.168.1.50:8000/api/v1`) und `CORS_ORIGINS` (z.B. `http://192.168.1.50:3000`) auf deine echte Server-Adresse setzen

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

Steht `"ollama":"unreachable"` da: `docker compose logs backend` checken, meist braucht das erste Modell-Laden noch ein paar Sekunden — kurz erneut versuchen.

Details/Hintergrund zur Modellwahl und VRAM-Begrenzung: [`infra/ollama/README.md`](./infra/ollama/README.md).

**Für Sprachsteuerung** (Speech-to-Text) zusätzlich `WHISPER_HOST`/`WHISPER_PORT` in `.env` prüfen — Default `host.docker.internal:10300` erreicht eine bestehende Wyoming-Whisper-Instanz auf demselben Server automatisch. Läuft sie woanders, hier die echte Adresse eintragen. Kurzer Check, ob sie erreichbar ist (nicht nur auf `127.0.0.1`, gleiches Prinzip wie bei Ollama):

```bash
ss -tlnp | grep 10300
```

## 4. Web-App starten und im Browser testen

Erstmal **ohne Caddy**, direkt per IP:Port — reicht völlig zum Testen im eigenen Netz (Caddy/Domain/TLS kommt in Schritt 6/7 dazu, falls gewünscht):

```bash
docker compose up -d web
```

Browser: `http://<server-ip>:3000` öffnen (die Server-IP in deinem lokalen Netz, `hostname -I` zeigt sie dir) — oder `http://localhost:3000`, falls du direkt am Server sitzt. Registrieren, einloggen — du landest direkt auf dem neuen „Voice"-Screen (Live Talk); für den ersten Test reicht aber auch einfach eine Text-Nachricht im „Chat"-Tab. Das ist der erste echte End-to-End-Test des ganzen Systems.

Live Talk (der Mikro-Kreis auf „Voice") braucht zusätzlich HTTPS oder `localhost` — siehe „Sprachsteuerung testen" weiter unten.

Falls etwas schiefgeht: `docker compose logs backend` bzw. `docker compose logs web`. Kommt beim Laden der Seite ein CORS-Fehler in der Browser-Konsole: `CORS_ORIGINS` in `.env` passt nicht zur URL, unter der du die Seite öffnest (siehe `.env.example`) — anpassen und `docker compose up -d backend` neu starten.

## 5. Kalender verbinden (optional, aber empfohlen zum Testen)

In der Web-App unter „Calendar" → „Connect CalDAV" deine echten Zugangsdaten eintragen (Apple/Google/Nextcloud-CalDAV-URL). Danach im Chat z. B. fragen: „Habe ich heute noch was vor?" — das testet den kompletten Tool-Calling-Pfad (LLM → Kalender-Tool → Antwort).

## 6. Netzwerkzugriff für deine Geräte einrichten

Empfehlung aus `DECISIONS.md`: **Tailscale**, damit iPad/PC/Handy den Server erreichen, ohne ihn öffentlich ins Internet zu stellen.

```bash
# auf dem Server:
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Dann Tailscale auch auf iPad, Windows-PC und S25 Ultra installieren (App Store / Microsoft Store / Play Store — das ist keine „eigene App", sondern ein Standard-VPN-Client) und alle im selben Tailnet einloggen. `tailscale ip -4` auf dem Server zeigt dir seine Tailscale-IP (bzw. `tailscale status` den Hostnamen).

**Einfachster Weg (empfohlen für den Start):** Caddy komplett weglassen, einfach direkt per Tailscale-IP/-Hostname + `BACKEND_PORT`/`WEB_PORT` zugreifen — Tailscale verschlüsselt den Traffic bereits selbst (WireGuard), eine zusätzliche TLS-Schicht über Caddy ist optional:

```bash
# NEXT_PUBLIC_API_BASE_URL und CORS_ORIGINS in .env auf die Tailscale-Adresse setzen, z.B.:
# NEXT_PUBLIC_API_BASE_URL=http://ownai-server:8000/api/v1
# CORS_ORIGINS=http://ownai-server:3000
docker compose up -d --build web   # Web-App neu bauen, da NEXT_PUBLIC_API_BASE_URL sich geändert hat
```

Web-App danach von jedem Gerät im Tailnet erreichbar: `http://ownai-server:3000` (Hostname/IP + `WEB_PORT` anpassen).

**Optional später:** Caddy davorschalten für eine „echte" HTTPS-Domain statt IP:Port. Dann `DOMAIN` in `.env` auf deine Domain bzw. den Tailscale-Hostnamen setzen, `NEXT_PUBLIC_API_BASE_URL`/`CORS_ORIGINS` wieder auskommentieren (Default greift dann: `https://${DOMAIN}/api/v1`), und:

```bash
docker compose up -d --build web caddy
```

## 7. Web-App als „App" auf iPad und PC installieren

- **iPad**: Safari öffnen, zur Web-App-URL aus Schritt 6 navigieren, Teilen-Button → „Zum Home-Bildschirm". Läuft danach im Vollbild mit eigenem Icon.
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

## Sprachsteuerung testen

- **Android**: Mikrofon-Button im Chat antippen, „Notification access"-artige Berechtigungsabfrage für Mikrofon bestätigen (einmalig), kurz sprechen, Button erneut antippen — der erkannte Text landet im Eingabefeld zum Prüfen/Bearbeiten vor dem Senden. Antworten werden automatisch vorgelesen, wenn du „Vorlesen" oben rechts im Chat aktivierst (oder tippe das Lautsprecher-Symbol an einer einzelnen Antwort an).
- **Web/PWA — „Voice" (Live Talk, vollautomatisch)**: der Mikro-Kreis-Screen, den du nach dem Login siehst. Einmal antippen zum Starten — danach läuft alles von selbst: sprechen, kurz Pause machen (~1,2s), die App transkribiert und schickt automatisch, die Antwort wird vorgelesen, danach hört sie automatisch wieder zu. Kein erneutes Antippen nötig, bis du auf „Beenden" tippst.
- **Web/PWA — Push-to-Talk im „Chat"-Tab**: Mikro-Button antippen → sprechen → nochmal antippen zum Stoppen → Text erscheint zur Kontrolle im Eingabefeld vor dem Senden. Eher für kurze, gezielte Nachrichten als für ein Gespräch.
- **Beides (Web) braucht HTTPS oder `localhost`** — Browser blockieren Mikrofonzugriff auf normalem `http://<ip>:<port>`. Du brauchst also entweder Schritt 6's Caddy-Option (echte Domain + HTTPS) oder Zugriff direkt über `http://localhost:<WEB_PORT>` (z. B. per SSH-Portweiterleitung vom PC aus). Ohne HTTPS ist das kein Bug, sondern eine Browser-Sicherheitsregel — der Rest der Web-App funktioniert trotzdem ganz normal, nur die Mikro-Funktionen bleiben ausgeblendet/inaktiv.
- Die Erkennung, wann du aufhörst zu reden (Live Talk), ist noch nicht an ein echtes Mikrofon/deinen Raum angepasst — falls Turns zu früh oder zu spät abgeschnitten werden, sag Bescheid, das lässt sich in `web/src/lib/useLiveTalk.ts` fein einstellen.

---

## Kurz-Checkliste zum Abhaken

- [ ] Docker + Docker Compose auf dem Server (Nvidia Container Toolkit nur nötig, falls du Schritt 1 für eine *neue* GPU-Nutzung durchgehst — deine bestehende Ollama-Instanz hat das vermutlich schon)
- [ ] `.env` ausgefüllt
- [ ] Modelle auf deiner bestehenden Ollama-Instanz gepullt, `curl localhost:11434/api/tags` erreichbar
- [ ] `docker compose up -d postgres redis backend`, `/health` zeigt `"ollama":"ok"`
- [ ] `docker compose up -d web`, Web-App im Browser getestet (Registrierung, Chat)
- [ ] CalDAV verbunden, Kalender-Tool im Chat getestet
- [ ] Tailscale auf Server + allen Geräten, `NEXT_PUBLIC_API_BASE_URL`/`CORS_ORIGINS` auf Tailscale-Adresse gesetzt, `web` neu gebaut
- [ ] Web-App auf iPad und PC als App installiert
- [ ] Android-App gebaut, per `adb install` aufs S25 Ultra, Notification-Zugriff gewährt, ein Vorschlag erfolgreich erzeugt
- [ ] Sprachsteuerung getestet: Android-Mikrofon-Button + Vorlesen; Web nur falls HTTPS/localhost verfügbar

Wenn du an einem Punkt hängen bleibst: einfach den Fehler/die Ausgabe hier reinkopieren, dann schauen wir's uns zusammen an.
