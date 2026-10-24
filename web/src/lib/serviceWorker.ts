/** Registers public/sw.js on every app start - not only when push gets enabled (see lib/push.ts)
 * - because the share target needs an active worker to receive shared images. Harmless without
 * push: the worker has no caching/offline logic. */
export function registerServiceWorker(): void {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
