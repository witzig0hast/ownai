# TTS-Server-Setup (Kokoro-Martin, optional)

## Warum ein eigener TTS-Server

Ohne diesen Schritt liest die Web-App Antworten weiterhin vor — aber nur über die im Browser
eingebaute `speechSynthesis`-API, deren Stimmqualität stark vom Gerät/OS abhängt und auf vielen
Linux-/Chrome-Setups eher robotisch klingt (siehe root `DECISIONS.md` #10). Dieser TTS-Server
ist der optionale Ersatz dafür: eine selbst gehostete, neurale Stimme, die deutlich natürlicher
klingt.

## Warum Kokoro-Martin (und nicht das offizielle Kokoro-82M)

Kokoro-82M selbst unterstützt **kein Deutsch offiziell** — nur Englisch, Mandarin und Japanisch
haben ein echtes Text-zu-Phonem-Frontend; alle anderen dokumentierten Sprachgruppen (inkl. der
Idee, deutschen Text einfach durchzujagen) würden englische Phoneme mit Akzent-Färbung liefern,
also eher schlechter klingen als vorher.

[`Godelaune/Kokoro-82M-ONNX-German-Martin`](https://github.com/Godelaune/Kokoro-82M-ONNX-German-Martin)
ist eine Community-Fine-Tune auf eine einzelne männliche deutsche Stimme ("Martin"), inkl.
eigenem fertigen Docker-Setup mit deutscher Textnormalisierung (Zahlen, Abkürzungen, Euro-Beträge
etc.). Bewusst gewählt trotz nur einer Stimme (keine Auswahl männlich/weiblich) — Alternative wäre
Piper mit mehreren offiziell unterstützten deutschen Stimmen, aber das ist hier bewusst die
Entscheidung für Kokoro gewesen (siehe Chat-Verlauf/Commit-Historie).

## Eigenständiger Stack, kein Teil von `docker-compose.yml`

Genau wie Ollama und Whisper bringt OwnAI diesen Server **nicht selbst mit** — er läuft als
eigener, separater Stack (eigenes Repo, eigene `docker-compose.yml`), und OwnAI verbindet sich
nur per HTTP darauf.

```bash
git clone https://github.com/Godelaune/Kokoro-82M-ONNX-German-Martin.git
cd Kokoro-82M-ONNX-German-Martin
sh scripts/download-model-files.sh
docker compose up -d --build
```

Das startet:
- **FastAPI-TTS-Dienst** auf Port `8881`, OpenAI-kompatibel unter `/v1/audio/speech`
  (Stimmenliste: `curl http://localhost:8881/v1/audio/voices`)
- **Wyoming-Protokoll-Server** auf Port `10203` (nur relevant für Home-Assistant-Integration,
  OwnAI nutzt das nicht)

Läuft rein CPU-basiert (die Env-Variablen im dortigen Compose-File, z.B.
`KOKORO_ONNX_INTRA_OP_THREADS`, sind ONNX-Runtime-Thread-Tuning, keine GPU-Flags) — konkurriert
also nicht mit Ollama um VRAM auf deiner P40.

## OwnAI daran anschließen

In deiner `.env`:

```bash
# Beispiel: Kokoro-Martin läuft auf demselben Host wie OwnAI
KOKORO_TTS_BASE_URL=http://host.docker.internal:8881
KOKORO_TTS_VOICE=martin
```

(`host.docker.internal` erreicht von den OwnAI-Containern aus den Host — dafür ist `extra_hosts`
im `backend`-Service in `docker-compose.yml` schon konfiguriert, genau wie bei
`OLLAMA_BASE_URL`/`WHISPER_HOST`.)

```bash
docker compose up -d --build backend
curl -X POST http://localhost:8000/api/v1/tts/speak \
  -H "Authorization: Bearer <dein-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hallo, ich bin dein Assistent."}' \
  --output test.mp3
```

Kommt eine gültige MP3-Datei zurück, ist die Verbindung OK. Testen lässt sich das genauso über
die Voice-Picker-Komponente in den Web-App-Einstellungen (Chat-Seite bzw. `/voice`) — der
"Testen"-Button spricht dort automatisch über den konfigurierten Server, sobald erreichbar.

## Fallback-Verhalten

`KOKORO_TTS_BASE_URL` leer lassen oder der Server nicht erreichbar → die Web-App fällt pro
Antwort automatisch und ohne Fehleranzeige auf die Browser-`speechSynthesis`-Stimme zurück (siehe
`web/src/lib/tts.ts`). Es gibt also keinen Zustand, in dem Vorlesen komplett ausfällt, nur einen
Qualitätsunterschied.
