/**
 * Text-to-speech, server-first: a self-hosted neural TTS server (see backend's
 * KOKORO_TTS_BASE_URL / app/services/tts_service.py) is tried first for a natural-sounding
 * voice, falling back to the browser's native Web Speech Synthesis API — entirely on-device,
 * no server round-trip — when the server isn't configured/reachable, or fails for any reason.
 * This keeps the app usable with zero setup (browser fallback always works) while sounding much
 * better once a TTS server is configured.
 *
 * Voice selection: browsers ship several synthesis voices (often including low-quality
 * offline ones like espeak/Piper alongside better online/OS voices), and which ones are
 * available/best varies per device — so this lets the user pick their preferred voice
 * once, persisted in localStorage, applied everywhere replies are read aloud. Same idea for
 * server voices, stored under a separate key (see VoicePicker.tsx).
 *
 * iOS Safari quirks (WebKit): both `speechSynthesis.speak()` and `<audio>.play()` only
 * reliably play when triggered synchronously inside a direct user-gesture handler (tap/click)
 * — a call made later from async code (e.g. after `await`ing a chat reply, which is how every
 * real reply gets read aloud) is silently swallowed: no error, no sound, nothing.
 * [unlockSpeech] works around this for both engines the same way `<audio>`/`AudioContext`
 * unlocking does elsewhere: call it once, synchronously, from the first real tap/click of the
 * session (before any `await`); that "unlocks" both engines for the rest of the session, so
 * later async speak() calls go through normally. Safari also has a separate, well-documented
 * bug where a long speechSynthesis utterance silently stops partway through after ~15s unless
 * kept alive — worked around here with a periodic pause/resume nudge while speaking (browser
 * fallback path only; server-synthesized audio plays via a normal <audio> element and isn't
 * affected).
 */

import * as ttsApi from "./api/tts";

const PREFERRED_VOICE_STORAGE_KEY = "ownai.preferredVoiceURI";
const PREFERRED_SERVER_VOICE_STORAGE_KEY = "ownai.preferredServerVoice";

// Tiny 1-sample silent WAV (8kHz mono 8-bit PCM) used purely to "unlock" <audio> autoplay on
// iOS Safari within a real user gesture - see file-level comment. Generated/verified with a
// real WAV encoder, not hand-typed base64.
const SILENT_WAV_DATA_URI =
  "data:audio/wav;base64,UklGRiUAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQEAAACA";

let unlocked = false;
let sharedAudio: HTMLAudioElement | null = null;

function getSharedAudio(): HTMLAudioElement {
  if (!sharedAudio) {
    sharedAudio = new Audio();
  }
  return sharedAudio;
}

export function isTtsSupported(): boolean {
  // Server TTS only needs <audio> playback, which is universal on any real browser - so this
  // is "true" almost everywhere now, not just where speechSynthesis exists.
  return typeof window !== "undefined" && (typeof Audio !== "undefined" || "speechSynthesis" in window);
}

function isBrowserTtsSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/**
 * Call once, synchronously, from a real tap/click handler (before any `await`) — see the
 * file-level comment for why. Safe to call repeatedly/from multiple places; only the first
 * call after each page load does anything.
 */
export function unlockSpeech(): void {
  if (unlocked || typeof window === "undefined") return;
  unlocked = true;

  if (isBrowserTtsSupported()) {
    try {
      const warmup = new SpeechSynthesisUtterance(" ");
      warmup.volume = 0;
      window.speechSynthesis.speak(warmup);
      window.speechSynthesis.cancel();
    } catch {
      // best-effort only — if this throws, real speak() calls will too, and get logged there
    }
  }

  if (typeof Audio !== "undefined") {
    try {
      const audio = getSharedAudio();
      audio.muted = true;
      audio.src = SILENT_WAV_DATA_URI;
      const playPromise = audio.play();
      if (playPromise) {
        playPromise
          .catch(() => {})
          .finally(() => {
            audio.pause();
            audio.muted = false;
          });
      }
    } catch {
      // best-effort only
    }
  }
}

export function getPreferredVoiceURI(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(PREFERRED_VOICE_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setPreferredVoiceURI(voiceURI: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (voiceURI) {
      window.localStorage.setItem(PREFERRED_VOICE_STORAGE_KEY, voiceURI);
    } else {
      window.localStorage.removeItem(PREFERRED_VOICE_STORAGE_KEY);
    }
  } catch {
    // best-effort only
  }
}

export function getPreferredServerVoice(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(PREFERRED_SERVER_VOICE_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setPreferredServerVoice(voice: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (voice) {
      window.localStorage.setItem(PREFERRED_SERVER_VOICE_STORAGE_KEY, voice);
    } else {
      window.localStorage.removeItem(PREFERRED_SERVER_VOICE_STORAGE_KEY);
    }
  } catch {
    // best-effort only
  }
}

/**
 * Resolves with the browser's available synthesis voices. Some browsers (notably Chrome)
 * load voices asynchronously — `getVoices()` can return an empty list on the first call,
 * populated only once the `voiceschanged` event fires — so this waits for that when needed
 * instead of just returning whatever's there immediately.
 */
export function getVoices(): Promise<SpeechSynthesisVoice[]> {
  if (!isBrowserTtsSupported()) return Promise.resolve([]);
  const synth = window.speechSynthesis;
  const existing = synth.getVoices();
  if (existing.length > 0) return Promise.resolve(existing);

  return new Promise((resolve) => {
    const onVoicesChanged = () => {
      synth.removeEventListener("voiceschanged", onVoicesChanged);
      resolve(synth.getVoices());
    };
    synth.addEventListener("voiceschanged", onVoicesChanged);
    // Some browsers never fire voiceschanged if there's nothing to report — don't hang forever.
    setTimeout(() => {
      synth.removeEventListener("voiceschanged", onVoicesChanged);
      resolve(synth.getVoices());
    }, 1000);
  });
}

/** Server TTS voices (empty if no server is configured) - see GET /tts/voices. */
export function getServerVoices(): Promise<string[]> {
  return ttsApi.listServerVoices().catch(() => []);
}

function applyPreferredVoice(utterance: SpeechSynthesisUtterance): void {
  const preferredURI = getPreferredVoiceURI();
  if (!preferredURI) return;
  const voice = window.speechSynthesis.getVoices().find((v) => v.voiceURI === preferredURI);
  if (voice) utterance.voice = voice;
}

/**
 * Works around a long-standing Safari/iOS bug where speech silently cuts off partway
 * through a longer utterance (~15s in) unless nudged. No-ops on browsers that don't need
 * it (calling pause/resume on an already-fine engine is harmless). Stops itself once
 * speech is no longer playing.
 */
function startKeepAlive(): () => void {
  if (!isBrowserTtsSupported()) return () => {};
  const interval = setInterval(() => {
    if (!window.speechSynthesis.speaking) {
      clearInterval(interval);
      return;
    }
    window.speechSynthesis.pause();
    window.speechSynthesis.resume();
  }, 5000);
  return () => clearInterval(interval);
}

function logSynthesisError(event: SpeechSynthesisErrorEvent): void {
  console.warn(`[tts] speechSynthesis error: ${event.error}`);
}

function speakViaBrowserAndWait(text: string, lang: string): Promise<void> {
  if (!isBrowserTtsSupported()) return Promise.resolve();
  window.speechSynthesis.cancel();
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    applyPreferredVoice(utterance);
    const stopKeepAlive = startKeepAlive();
    utterance.onend = () => {
      stopKeepAlive();
      resolve();
    };
    utterance.onerror = (event) => {
      stopKeepAlive();
      logSynthesisError(event);
      resolve();
    };
    window.speechSynthesis.speak(utterance);
  });
}

/** Null if the server has nothing configured/reachable - callers fall back to browser TTS. */
async function synthesizeViaServer(text: string): Promise<Blob | null> {
  try {
    return await ttsApi.synthesizeSpeech(text, getPreferredServerVoice() ?? undefined);
  } catch {
    return null;
  }
}

export function speak(text: string, lang = "de-DE"): void {
  if (!text.trim()) return;
  void speakAndWait(text, lang);
}

export function stopSpeaking(): void {
  if (sharedAudio && !sharedAudio.paused) {
    sharedAudio.pause();
    sharedAudio.currentTime = 0;
  }
  if (isBrowserTtsSupported()) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Speaks `text` aloud, resolving once playback finishes (or immediately if TTS isn't
 * supported / the text is empty) — used by the Live Talk loop to know when it's safe to start
 * listening again. Resolves rather than rejects on any failure, since a failed read-aloud
 * shouldn't break the conversation loop. Tries the self-hosted server voice first, falling
 * back to the browser's built-in one.
 */
export async function speakAndWait(text: string, lang = "de-DE"): Promise<void> {
  if (!isTtsSupported() || !text.trim()) return;
  stopSpeaking();

  const blob = await synthesizeViaServer(text);
  if (!blob) {
    return speakViaBrowserAndWait(text, lang);
  }

  const audio = getSharedAudio();
  const url = URL.createObjectURL(blob);
  audio.src = url;
  return new Promise((resolve) => {
    const cleanup = () => {
      audio.removeEventListener("ended", onEnd);
      audio.removeEventListener("error", onError);
      URL.revokeObjectURL(url);
    };
    const onEnd = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      // Playback itself failed (e.g. unsupported format) - fall back to browser TTS rather
      // than silently producing no audio at all.
      speakViaBrowserAndWait(text, lang).then(resolve);
    };
    audio.addEventListener("ended", onEnd);
    audio.addEventListener("error", onError);
    audio.play().catch(onError);
  });
}
