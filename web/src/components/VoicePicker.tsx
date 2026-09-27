"use client";

import { useEffect, useState } from "react";
import { getPreferredVoiceURI, getVoices, isTtsSupported, setPreferredVoiceURI, speak } from "@/lib/tts";

/**
 * Lets the user pick which browser/OS voice reads replies aloud. Some devices default to
 * a low-quality offline voice (e.g. an espeak/Piper-based one on Linux) that sounds robotic
 * — this surfaces every voice the platform offers so the user can pick a better one, without
 * needing a server-side TTS engine (see root DECISIONS.md #10).
 */
export function VoicePicker() {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!isTtsSupported()) return;
    let cancelled = false;
    getVoices().then((list) => {
      if (cancelled) return;
      setVoices(list);
      setSelected(getPreferredVoiceURI() ?? "");
      setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!isTtsSupported() || !loaded || voices.length === 0) return null;

  const germanFirst = [...voices].sort((a, b) => {
    const aDe = a.lang.toLowerCase().startsWith("de") ? 0 : 1;
    const bDe = b.lang.toLowerCase().startsWith("de") ? 0 : 1;
    return aDe - bDe || a.name.localeCompare(b.name);
  });

  const handleChange = (voiceURI: string) => {
    setSelected(voiceURI);
    setPreferredVoiceURI(voiceURI || null);
    const voice = voices.find((v) => v.voiceURI === voiceURI);
    speak(voice ? `Hallo, ich bin ${voice.name}.` : "Hallo, das ist die Standardstimme.");
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
        className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
      >
        <option value="">Systemstandard</option>
        {germanFirst.map((voice) => (
          <option key={voice.voiceURI} value={voice.voiceURI}>
            {voice.name} ({voice.lang})
          </option>
        ))}
      </select>
    </div>
  );
}
