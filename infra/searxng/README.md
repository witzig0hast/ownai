# SearXNG-Setup (optional, für Web-Suche)

## Warum eine eigene SearXNG-Instanz

Der `web_search`-Tool des Assistenten (`backend/app/services/searxng_service.py`) braucht eine
selbst gehostete [SearXNG](https://docs.searxng.org/)-Instanz — eine Meta-Suchmaschine, die
Ergebnisse von Google/Bing/DuckDuckGo/etc. bündelt, ohne dass du bei einem dieser Anbieter einen
API-Key brauchst. OwnAI ruft nur `GET <deine-url>/search?q=...&format=json` auf — unauthentifiziert,
kein Token nötig, solange die Instanz nur in deinem privaten Netz erreichbar ist (siehe root
`DECISIONS.md` #2).

## Eigenständiger Stack, kein Teil von `docker-compose.yml`

Genau wie Ollama/Whisper/Kokoro bringt OwnAI SearXNG **nicht selbst mit** — es läuft als eigener,
separater Stack, und OwnAI verbindet sich nur per HTTP darauf. Die `searxng-docker`-Referenz war
lange der Standardweg, ist aber inzwischen archiviert — das hier folgt der aktuellen offiziellen
Anleitung ([docs.searxng.org](https://docs.searxng.org/admin/installation-docker.html)).

```bash
mkdir -p ./searxng/core-config/
cd ./searxng/

curl -fsSL \
  -O https://raw.githubusercontent.com/searxng/searxng/master/container/docker-compose.yml \
  -O https://raw.githubusercontent.com/searxng/searxng/master/container/.env.example

cp .env.example .env
# .env optional anpassen (Version/Host/Port pinnen) - Default-Port ist 8080

docker compose up -d
```

Der erste Start legt automatisch eine Standard-`core-config/settings.yml` an (Volume war vorher
leer). Danach einmal stoppen, die Datei anpassen und neu starten:

```bash
docker compose down
```

In `core-config/settings.yml` **ein Ding zwingend ändern und eins zur Sicherheit prüfen**:

```yaml
server:
  secret_key: "hier-einen-eigenen-zufälligen-wert-eintragen"  # niemals den Default behalten
  limiter: false  # Standardwert, hier nur zur Klarheit explizit gesetzt - Bot-/Rate-Limiter aus,
                   # weil die Instanz privat ist und nur OwnAIs Backend bedient; ein aktiver
                   # Limiter blockt automatisierte JSON-Anfragen wie OwnAIs sonst als "Bot"

search:
  formats:
    - html
    - json  # zwingend nötig - ohne diesen Eintrag liefert /search?format=json einen 403
            # (Standardverhalten von SearXNG, JSON-Output ist aus Missbrauchsschutz-Gründen
            # per Default deaktiviert)
```

Dann wieder starten:

```bash
docker compose up -d
```

## OwnAI daran anschließen

Testen, dass JSON tatsächlich funktioniert:

```bash
curl "http://localhost:8080/search?q=test&format=json"
```

Kommt gültiges JSON zurück (nicht `403 Forbidden`), in der Web-App unter **Settings →
Integrations → Web-Suche** die URL eintragen, unter der dein Backend die Instanz erreicht — z.B.
`http://host.docker.internal:8080`, wenn SearXNG auf demselben Host wie OwnAI läuft
(`host.docker.internal` erreicht von den OwnAI-Containern aus den Host — dafür ist `extra_hosts`
im `backend`-Service in `docker-compose.yml` schon konfiguriert, genau wie bei
`OLLAMA_BASE_URL`/`WHISPER_HOST`/`KOKORO_TTS_BASE_URL`). Kein Backend-Neustart nötig — die URL
wird pro Nutzer in der Datenbank gespeichert (`SearxngAccount`), nicht über `.env`.

## Wichtig, falls du die Instanz später öffentlich exponierst

Diese Anleitung ist bewusst auf "privat, nur im eigenen Netz erreichbar" ausgelegt (Limiter aus).
Machst du die Instanz später doch öffentlich erreichbar, unbedingt `server.limiter: true` (plus
eine Valkey-gestützte Bot-Erkennung, siehe `core-config/limiter.toml` und die offizielle
Doku) wieder aktivieren — sonst kann jeder im Internet deine Instanz für eigene Anfragen
missbrauchen.
