# Ollama-Setup auf dem Tesla-P40-Server

## Warum Ollama (und nicht vLLM/TGI) auf der P40

Die Tesla P40 (Pascal, `sm_61`) hat **keine Tensor Cores** und schwache natives FP16 — sie ist für FP32/INT8 ausgelegt. Ollama nutzt intern `llama.cpp` mit GGUF-Quantisierung (Q4_K_M etc.), was auf der P40 gut und stabil läuft. Frameworks, die auf schnelles natives FP16/BF16 setzen (vLLM, TGI Standard-Modus), sind hier die falsche Wahl.

## Modellwahl

- Hauptmodell: **`hermes3:8b`** (Nous Research, starkes Tool-/Function-Calling, ~5–6 GB VRAM in Q4_K_M)
- Alternative mit mehr Reasoning-Tiefe, falls VRAM-Budget es zulässt: **`hermes3:latest`** (im Ollama-Library-Default aktuell ~70B via mehrerer Quant-Stufen — **passt nicht** in 24 GB, daher nicht empfohlen) oder ein Zwischenschritt wie ein 14B-Hermes-Finetune, falls verfügbar.
- Embeddings (RAG/Langzeitgedächtnis): **`nomic-embed-text`** (~0,3 GB)

> Bewusst **nicht das volle VRAM ausschöpfen**: mit `hermes3:8b` liegt die Grundlast bei ca. 6–8 GB, das lässt reichlich Puffer für Embeddings, parallele Anfragen und späteres Whisper-STT (Phase 6) auf denselben 24 GB.

## Bereits vorhandene Ollama-Instanz nutzen (Standardfall)

`docker-compose.yml` startet standardmäßig **kein eigenes Ollama** — wenn auf dem Server schon eines läuft (systemd-Install oder eigener Container), wird das genutzt. Zwei Dinge dafür prüfen/einrichten:

1. **Modell pullen**, auf deiner bestehenden Instanz:
   ```bash
   ollama pull hermes3:8b
   ollama pull nomic-embed-text
   ```
   (bei einer eigenen Ollama-Docker-Instanz entsprechend `docker exec -it <dein-ollama-container> ollama pull hermes3:8b`)

2. **Erreichbarkeit von den OwnAI-Containern aus** — Ollama muss auf mehr als nur `127.0.0.1` lauschen, sonst kommt `docker-compose`s `backend`-Container nicht ran (Container sehen den Host nicht als „localhost"):
   ```bash
   # prüfen, ob schon offen:
   curl http://localhost:11434/api/tags
   ss -tlnp | grep 11434   # zeigt, ob es auf 127.0.0.1 oder 0.0.0.0 lauscht
   ```
   Steht da nur `127.0.0.1:11434`, bei einer systemd-Installation fixen:
   ```bash
   sudo systemctl edit ollama
   # einfügen:
   #   [Service]
   #   Environment="OLLAMA_HOST=0.0.0.0:11434"
   sudo systemctl restart ollama
   ```
   Läuft dein Ollama in einem eigenen Container: sicherstellen, dass er mit `-p 11434:11434` (oder äquivalent in dessen eigener Compose-Datei) auf den Host published.

`OLLAMA_BASE_URL` in `.env` bleibt dann auf dem Default `http://host.docker.internal:11434` — die OwnAI-Container erreichen den Host darüber (dafür ist `extra_hosts` im `backend`-Service in `docker-compose.yml` schon konfiguriert). Testen:

```bash
docker compose up -d backend
curl http://localhost:8000/api/v1/health
# erwartet: {"status":"ok","ollama":"ok"}
```

## Alternative: den mitgelieferten Ollama-Service nutzen

Nur nötig, wenn du **kein** eigenes Ollama hast:

```bash
docker compose --profile bundled-ollama up -d ollama
docker exec -it ownai-ollama ollama pull hermes3:8b
docker exec -it ownai-ollama ollama pull nomic-embed-text
```

Dann in `.env`: `OLLAMA_BASE_URL=http://ollama:11434` (auskommentierte Zeile in `.env.example` aktivieren).

## VRAM unter Kontrolle halten

Nutzt du den mitgelieferten Service, in `.env` (siehe `.env.example`):

```
OLLAMA_MAX_LOADED_MODELS=1   # nur 1 Modell gleichzeitig im VRAM
OLLAMA_KEEP_ALIVE=10m        # entlädt Modell nach 10 Min. Inaktivität
```

Damit bleibt der Server im Ruhezustand VRAM-frei und lädt bei Bedarf nach (kostet die ersten ~1–3 Sekunden Ladezeit pro „kalter" Anfrage — akzeptabler Trade-off für einen persönlichen Assistenten, der nicht dauerhaft angefragt wird). Läuft dein eigenes Ollama bereits, stell das Äquivalent dort ein (z.B. `OLLAMA_MAX_LOADED_MODELS`/`OLLAMA_KEEP_ALIVE` als systemd-Environment-Variablen für den `ollama`-Dienst).

## Wechsel auf ein größeres Modell später

Falls du später einen zweiten GPU-Slot oder mehr VRAM hast: einfach `OLLAMA_CHAT_MODEL` in `.env` ändern (z. B. auf ein 14B/32B-Modell) und `docker exec ownai-ollama ollama pull <modell>` — der Backend-Code (`backend/app/agent/`) ist modellunabhängig, solange das Modell Tool-Calling unterstützt (Ollama-Tool-Calling-kompatible Modelle, siehe [ollama.com/search?c=tools](https://ollama.com/search?c=tools)).
