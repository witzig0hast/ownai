import * as chatApi from "./api/chat";

/**
 * Deduped wrapper around chatApi.warmup(). Every authenticated page (AppShell) and Chat/Voice's
 * own mount both call this - without dedup that means the same "load the LLM" request fires
 * repeatedly as the user navigates around, adding load to Ollama for nothing. Within this
 * window, everyone gets back the *same* in-flight/settled promise instead of firing a new
 * request, so `await`ing it still tells a caller (e.g. the Voice page) exactly when the model
 * is actually ready, no matter which page triggered the real network call.
 */
const DEDUPE_WINDOW_MS = 4 * 60 * 1000;

let pending: Promise<void> | null = null;
let firedAt = 0;

export function warmupOnce(): Promise<void> {
  const now = Date.now();
  if (pending && now - firedAt < DEDUPE_WINDOW_MS) {
    return pending;
  }
  firedAt = now;
  pending = chatApi.warmup().catch(() => {
    // Let a later call retry soon rather than waiting out the full window on a failed attempt
    // (e.g. Ollama briefly unreachable) - best-effort either way, callers never need to handle
    // this themselves.
    firedAt = 0;
  });
  return pending;
}
