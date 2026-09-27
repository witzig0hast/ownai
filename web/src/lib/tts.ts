/**
 * Text-to-speech via the browser's native Web Speech Synthesis API — runs entirely
 * on-device, no server round-trip, no cost (see root DECISIONS.md: voice input goes
 * through the user's own self-hosted Whisper, but reading replies aloud doesn't need
 * that at all, so it stays client-side and free everywhere it runs).
 *
 * Voice selection: browsers ship several synthesis voices (often including low-quality
 * offline ones like espeak/Piper alongside better online/OS voices), and which ones are
 * available/best varies per device — so this lets the user pick their preferred voice
 * once, persisted in localStorage, applied everywhere replies are read aloud.
 *
 * iOS Safari quirks (WebKit): `speechSynthesis.speak()` only reliably plays when called
 * synchronously inside a direct user-gesture handler (tap/click) — a call made later from
 * async code (e.g. after `await`ing a chat reply, which is how every real reply gets read
 * aloud) is silently swallowed: no error, no sound, nothing. [unlockSpeech] works around
 * this the same way `<audio>`/`AudioContext` unlocking does elsewhere: call it once,
 * synchronously, from the first real tap/click of the session (before any `await`); that
 * "unlocks" speech synthesis for the rest of the session, so later async `speak()` calls
 * go through normally. Safari also has a separate, well-documented bug where a long
 * utterance silently stops partway through after ~15s unless kept alive — worked around
 * here with a periodic pause/resume nudge while speaking.
 */

const PREFERRED_VOICE_STORAGE_KEY = "ownai.preferredVoiceURI";

let unlocked = false;

export function isTtsSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/**
 * Call once, synchronously, from a real tap/click handler (before any `await`) — see the
 * file-level comment for why. Safe to call repeatedly/from multiple places; only the first
 * call after each page load does anything.
 */
export function unlockSpeech(): void {
  if (unlocked || !isTtsSupported()) return;
  unlocked = true;
  try {
    const warmup = new SpeechSynthesisUtterance(" ");
    warmup.volume = 0;
    window.speechSynthesis.speak(warmup);
    window.speechSynthesis.cancel();
  } catch {
    // best-effort only — if this throws, real speak() calls will too, and get logged there
  }
}

/**
 * Resolves with the browser's available synthesis voices. Some browsers (notably Chrome)
 * load voices asynchronously — `getVoices()` can return an empty list on the first call,
 * populated only once the `voiceschanged` event fires — so this waits for that when needed
 * instead of just returning whatever's there immediately.
 */
export function getVoices(): Promise<SpeechSynthesisVoice[]> {
  if (!isTtsSupported()) return Promise.resolve([]);
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
  if (!isTtsSupported()) return () => {};
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

export function speak(text: string, lang = "de-DE"): void {
  if (!isTtsSupported() || !text.trim()) return;
  window.speechSynthesis.cancel(); // don't stack replies if one is already playing
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  applyPreferredVoice(utterance);
  const stopKeepAlive = startKeepAlive();
  utterance.onend = stopKeepAlive;
  utterance.onerror = (event) => {
    stopKeepAlive();
    logSynthesisError(event);
  };
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (isTtsSupported()) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Like [speak], but resolves once playback finishes (or immediately if TTS isn't
 * supported / the text is empty) — used by the Live Talk loop to know when it's safe
 * to start listening again. Resolves rather than rejects on a synthesis error, since a
 * failed read-aloud shouldn't break the conversation loop.
 */
export function speakAndWait(text: string, lang = "de-DE"): Promise<void> {
  if (!isTtsSupported() || !text.trim()) return Promise.resolve();
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
