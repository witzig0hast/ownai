"use client";

import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { VoicePicker } from "@/components/VoicePicker";
import * as chatApi from "@/lib/api/chat";
import { useArtifactPanel } from "@/lib/artifactPanel";
import { parseMessageContent } from "@/lib/parseMessageContent";
import { unlockSpeech } from "@/lib/tts";
import { useLiveTalk, type LiveTalkState } from "@/lib/useLiveTalk";

const STATE_LABEL: Record<LiveTalkState, string> = {
  idle: "Tippen zum Starten",
  listening: "Ich höre zu…",
  transcribing: "Transkribiere…",
  thinking: "Denke nach…",
  speaking: "Antwort…",
};

const STATE_RING_COLOR: Record<LiveTalkState, string> = {
  idle: "bg-zinc-300 dark:bg-zinc-700",
  listening: "bg-indigo-500",
  transcribing: "bg-amber-500",
  thinking: "bg-violet-500",
  speaking: "bg-emerald-500",
};

function MicGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-10 w-10 text-white" aria-hidden="true">
      <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z" stroke="currentColor" strokeWidth={2} />
      <path d="M19 11a7 7 0 0 1-14 0M12 18v3" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function MuteIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v3" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <path d="M19 11a7 7 0 0 1-1.4 4.2M4 4l16 16" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <path d="M12 18v3" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
      <path
        d="M6 3h9l3 3v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      <path d="M14 3v4a1 1 0 0 0 1 1h4" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5 shrink-0" aria-hidden="true">
      <path d="m8 8-4 4 4 4M16 8l4 4-4 4" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function VoicePage() {
  const {
    state,
    volume,
    lastUserText,
    lastAssistantText,
    lastToolCalls,
    conversationId,
    error,
    isSupported,
    muted,
    start,
    stop,
    toggleMute,
    interrupt,
  } = useLiveTalk();
  const { openArtifact } = useArtifactPanel();

  const isActive = state !== "idle";
  // Ring grows a bit with mic volume while actively listening, otherwise pulses gently.
  const scale = state === "listening" ? 1 + Math.min(volume, 1) * 0.35 : 1;
  const stateLabel = muted && state === "listening" ? "Stummgeschaltet" : STATE_LABEL[state];

  // Voice has no message thread to render code blocks/download links inline in (unlike Chat) -
  // strip fenced code from the displayed text (still spoken in full by tts, code isn't useful
  // read aloud anyway) and surface it plus any generated file as Artifact Panel buttons instead.
  const segments = lastAssistantText ? parseMessageContent(lastAssistantText) : [];
  const displayAssistantText = segments
    .filter((s) => s.type === "text")
    .map((s) => s.value)
    .join(" ")
    .trim();
  const codeSegment = segments.find((s) => s.type === "code");
  const fileToolCalls = (lastToolCalls || []).filter(
    (tc) => tc.tool === "create_file" && typeof tc.result.id === "string" && typeof tc.result.filename === "string",
  );

  // Loads the model into Ollama ahead of time, so the first reply in this session doesn't pay
  // for the load - best-effort, a failure here shouldn't surface as a user-facing error.
  useEffect(() => {
    chatApi.warmup().catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 p-8">
        {!isSupported ? (
          <ErrorMessage message="Live Talk braucht Mikrofonzugriff (getUserMedia) und Web Audio - dein Browser oder diese Verbindung unterstützt das nicht. Läuft die Seite über http:// statt https:// oder localhost, blockieren Browser den Mikrofonzugriff komplett." />
        ) : (
          <>
            <button
              type="button"
              onClick={() => {
                if (isActive) {
                  stop();
                } else {
                  unlockSpeech(); // must run synchronously in this click handler - see tts.ts
                  start();
                }
              }}
              className="relative flex h-40 w-40 items-center justify-center rounded-full transition-transform duration-150 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-300"
              style={{ transform: `scale(${scale})` }}
            >
              <span
                className={`absolute inset-0 rounded-full transition-colors duration-300 ${
                  muted && state === "listening" ? "bg-zinc-400 dark:bg-zinc-600" : STATE_RING_COLOR[state]
                } ${state === "thinking" || state === "speaking" || (state === "listening" && !muted) ? "animate-pulse" : ""}`}
              />
              <span className="relative flex h-full w-full items-center justify-center rounded-full">
                <MicGlyph />
              </span>
            </button>

            <div className="text-center">
              <p className="text-lg font-medium text-zinc-900 dark:text-zinc-100">{stateLabel}</p>
              {!isActive ? (
                <>
                  <p className="mt-1 text-sm text-zinc-500">
                    Ein Gespräch ohne Tippen — sprich, die Antwort kommt automatisch als Sprache zurück.
                  </p>
                  <div className="mx-auto mt-4 max-w-xs">
                    <VoicePicker />
                  </div>
                </>
              ) : (
                <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                  <button
                    type="button"
                    onClick={toggleMute}
                    title={muted ? "Mikrofon wieder aktivieren" : "Mikrofon stummschalten"}
                    className={`flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
                      muted
                        ? "border-amber-400 bg-amber-50 text-amber-700 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300"
                        : "border-zinc-300 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    }`}
                  >
                    <MuteIcon />
                    {muted ? "Stumm" : "Stummschalten"}
                  </button>
                  {state === "speaking" ? (
                    <button
                      type="button"
                      onClick={interrupt}
                      className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      Unterbrechen
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={stop}
                    className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                  >
                    Beenden
                  </button>
                </div>
              )}
            </div>

            {(lastUserText || lastAssistantText) && (
              <div className="w-full max-w-md space-y-3 text-center">
                {lastUserText ? (
                  <p className="text-sm text-zinc-500">
                    <span className="font-medium text-zinc-700 dark:text-zinc-300">Du:</span> {lastUserText}
                  </p>
                ) : null}
                {displayAssistantText ? (
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">
                    <span className="font-medium">OwnAI:</span> {displayAssistantText}
                  </p>
                ) : null}
                {fileToolCalls.length > 0 || codeSegment ? (
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    {conversationId
                      ? fileToolCalls.map((tc, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() =>
                              openArtifact({
                                type: "file",
                                conversationId,
                                fileId: tc.result.id as string,
                                filename: tc.result.filename as string,
                                sizeBytes:
                                  typeof tc.result.size_bytes === "number" ? tc.result.size_bytes : undefined,
                              })
                            }
                            className="flex items-center gap-1.5 rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                          >
                            <FileIcon /> {tc.result.filename as string}
                          </button>
                        ))
                      : null}
                    {codeSegment && codeSegment.type === "code" ? (
                      <button
                        type="button"
                        onClick={() =>
                          codeSegment.type === "code" &&
                          openArtifact({ type: "code", language: codeSegment.language, code: codeSegment.value })
                        }
                        className="flex items-center gap-1.5 rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                      >
                        <CodeIcon /> Code anzeigen
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}

            {error ? (
              <div className="w-full max-w-md">
                <ErrorMessage message={error} />
              </div>
            ) : null}
          </>
        )}
      </div>
    </AppShell>
  );
}
