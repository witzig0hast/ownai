/**
 * Text-to-speech via the browser's native Web Speech Synthesis API — runs entirely
 * on-device, no server round-trip, no cost (see root DECISIONS.md: voice input goes
 * through the user's own self-hosted Whisper, but reading replies aloud doesn't need
 * that at all, so it stays client-side and free everywhere it runs).
 */

export function isTtsSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function speak(text: string, lang = "de-DE"): void {
  if (!isTtsSupported() || !text.trim()) return;
  window.speechSynthesis.cancel(); // don't stack replies if one is already playing
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking(): void {
  if (isTtsSupported()) {
    window.speechSynthesis.cancel();
  }
}
