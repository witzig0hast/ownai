"use client";

import { useEffect, useState } from "react";
import {
  getPreferredServerVoice,
  getPreferredVoiceURI,
  getServerVoices,
  getVoices,
  isTtsSupported,
  setPreferredServerVoice,
  setPreferredVoiceURI,
  speak,
  unlockSpeech,
} from "@/lib/tts";

/**
 * Lets the user pick which voice reads replies aloud. Prefers the self-hosted TTS server's
 * voices when one is configured (see backend KOKORO_TTS_BASE_URL) — usually just one natural
 * neural voice, but still worth letting the user confirm/test it — and falls back to the
 * browser/OS's built-in voices otherwise. Some devices default to a low-quality offline voice
 * (e.g. an espeak/Piper-based one on Linux) that sounds robotic — surfacing every voice the
 * platform offers lets the user pick a better one even without a configured TTS server.
 */
export function VoicePicker() {
  const [serverVoices, setServerVoices] = useState<string[]>([]);
  const [browserVoices, setBrowserVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!isTtsSupported()) return;
    let cancelled = false;
    Promise.all([getServerVoices(), getVoices()]).then(([serverList, browserList]) => {
      if (cancelled) return;
      setServerVoices(serverList);
      setBrowserVoices(browserList);
      setSelected((serverList.length > 0 ? getPreferredServerVoice() : getPreferredVoiceURI()) ?? "");
      setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const usingServerVoices = serverVoices.length > 0;

  if (!isTtsSupported() || !loaded || (serverVoices.length === 0 && browserVoices.length === 0)) return null;

  const germanFirst = [...browserVoices].sort((a, b) => {
    const aDe = a.lang.toLowerCase().startsWith("de") ? 0 : 1;
    const bDe = b.lang.toLowerCase().startsWith("de") ? 0 : 1;
    return aDe - bDe || a.name.localeCompare(b.name);
  });

  const speakSample = (value: string) => {
    // Native <select> "change" events aren't a reliably "trusted" gesture on every
    // platform (notably iOS Safari, where the picker is a system sheet) - unlock
    // defensively here too, even though it's a no-op after the first real call.
    unlockSpeech();
    const label = usingServerVoices
      ? value || "der Standardstimme"
      : (browserVoices.find((v) => v.voiceURI === value)?.name ?? null);
    speak(label ? `Hallo, ich bin ${label}.` : "Hallo, das ist die Standardstimme.");
  };

  const handleChange = (value: string) => {
    setSelected(value);
    if (usingServerVoices) {
      setPreferredServerVoice(value || null);
    } else {
      setPreferredVoiceURI(value || null);
    }
    speakSample(value);
  };

  return (
    <div className="flex items-center gap-2 text-sm text-zinc-500">
      <label htmlFor="voice-picker" className="shrink-0">
        Stimme
      </label>
      <select
        id="voice-picker"
        value={selected}
        onChange={(e) => handleChange(e.target.value)}
        className="min-w-0 flex-1 rounded-xl border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-700 transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
      >
        <option value="">Systemstandard</option>
        {usingServerVoices
          ? serverVoices.map((voice) => (
              <option key={voice} value={voice}>
                {voice}
              </option>
            ))
          : germanFirst.map((voice) => (
              <option key={voice.voiceURI} value={voice.voiceURI}>
                {voice.name} ({voice.lang})
              </option>
            ))}
      </select>
      <button
        type="button"
        onClick={() => speakSample(selected)}
        title="Stimme testen"
        className="shrink-0 rounded-full border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-600 transition-all hover:scale-105 hover:bg-zinc-100 active:scale-95 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
      >
        Testen
      </button>
    </div>
  );
}
