# Ollama-Setup auf dem Tesla-P40-Server

## Warum Ollama (und nicht vLLM/TGI) auf der P40

Die Tesla P40 (Pascal, `sm_61`) hat **keine Tensor Cores** und schwache natives FP16 — sie ist für FP32/INT8 ausgelegt. Ollama nutzt intern `llama.cpp` mit GGUF-Quantisierung (Q4_K_M etc.), was auf der P40 gut und stabil läuft. Frameworks, die auf schnelles natives FP16/BF16 setzen (vLLM, TGI Standard-Modus), sind hier die falsche Wahl.

## Modellwahl

- Hauptmodell: **`hermes3:8b`** (Nous Research, starkes Tool-/Function-Calling, ~5–6 GB VRAM in Q4_K_M)
- Alternative mit mehr Reasoning-Tiefe, falls VRAM-Budget es zulässt: **`hermes3:latest`** (im Ollama-Library-Default aktuell ~70B via mehrerer Quant-Stufen — **passt nicht** in 24 GB, daher nicht empfohlen) oder ein Zwischenschritt wie ein 14B-Hermes-Finetune, falls verfügbar.
- Embeddings (RAG/Langzeitgedächtnis): **`nomic-embed-text`** (~0,3 GB)

> Bewusst **nicht das volle VRAM ausschöpfen**: mit `hermes3:8b` liegt die Grundlast bei ca. 6–8 GB, das lässt reichlich Puffer für Embeddings, parallele Anfragen und späteres Whisper-STT (Phase 6) auf denselben 24 GB.

## Einrichtung

```bash
# einmalig, nach docker compose up -d ollama
docker exec -it ownai-ollama ollama pull hermes3:8b
docker exec -it ownai-ollama ollama pull nomic-embed-text

# Modell testen
curl http://localhost:11434/api/generate -d '{
  "model": "hermes3:8b",
  "prompt": "Sag in einem Satz, wer du bist.",
  "stream": false
}'
```

## VRAM unter Kontrolle halten

In `.env` (siehe `.env.example`):

```
OLLAMA_MAX_LOADED_MODELS=1   # nur 1 Modell gleichzeitig im VRAM
OLLAMA_KEEP_ALIVE=10m        # entlädt Modell nach 10 Min. Inaktivität
```

Damit bleibt der Server im Ruhezustand VRAM-frei und lädt bei Bedarf nach (kostet die ersten ~1–3 Sekunden Ladezeit pro „kalter" Anfrage — akzeptabler Trade-off für einen persönlichen Assistenten, der nicht dauerhaft angefragt wird).

## Wechsel auf ein größeres Modell später

Falls du später einen zweiten GPU-Slot oder mehr VRAM hast: einfach `OLLAMA_CHAT_MODEL` in `.env` ändern (z. B. auf ein 14B/32B-Modell) und `docker exec ownai-ollama ollama pull <modell>` — der Backend-Code (`backend/app/agent/`) ist modellunabhängig, solange das Modell Tool-Calling unterstützt (Ollama-Tool-Calling-kompatible Modelle, siehe [ollama.com/search?c=tools](https://ollama.com/search?c=tools)).
