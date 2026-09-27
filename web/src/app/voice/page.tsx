"use client";

import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { VoicePicker } from "@/components/VoicePicker";
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

export default function VoicePage() {
  const { state, volume, lastUserText, lastAssistantText, error, isSupported, start, stop } = useLiveTalk();

  const isActive = state !== "idle";
  // Ring grows a bit with mic volume while actively listening, otherwise pulses gently.
  const scale = state === "listening" ? 1 + Math.min(volume, 1) * 0.35 : 1;

  return (
    <AppShell>
      <div className="flex flex-1 flex-col items-center justify-center gap-8 p-8">
        {!isSupported ? (
          <ErrorMessage message="Live Talk braucht Mikrofonzugriff (getUserMedia) und Web Audio - dein Browser oder diese Verbindung unterstützt das nicht. Läuft die Seite über http:// statt https:// oder localhost, blockieren Browser den Mikrofonzugriff komplett." />
        ) : (
          <>
            <button
              type="button"
              onClick={() => (isActive ? stop() : start())}
              className="relative flex h-40 w-40 items-center justify-center rounded-full transition-transform duration-150 focus:outline-none focus-visible:ring-4 focus-visible:ring-indigo-300"
              style={{ transform: `scale(${scale})` }}
            >
              <span
                className={`absolute inset-0 rounded-full transition-colors duration-300 ${STATE_RING_COLOR[state]} ${
                  state === "listening" || state === "thinking" || state === "speaking" ? "animate-pulse" : ""
                }`}
              />
              <span className="relative flex h-full w-full items-center justify-center rounded-full">
                <MicGlyph />
              </span>
            </button>

            <div className="text-center">
              <p className="text-lg font-medium text-zinc-900 dark:text-zinc-100">{STATE_LABEL[state]}</p>
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
                <button
                  type="button"
                  onClick={stop}
                  className="mt-3 rounded-md border border-zinc-300 px-4 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                >
                  Beenden
                </button>
              )}
            </div>

            {(lastUserText || lastAssistantText) && (
              <div className="w-full max-w-md space-y-3 text-center">
                {lastUserText ? (
                  <p className="text-sm text-zinc-500">
                    <span className="font-medium text-zinc-700 dark:text-zinc-300">Du:</span> {lastUserText}
                  </p>
                ) : null}
                {lastAssistantText ? (
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">
                    <span className="font-medium">OwnAI:</span> {lastAssistantText}
                  </p>
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
