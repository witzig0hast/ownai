import * as pushApi from "./api/push";

export function isPushSupported(): boolean {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window;
}

// The browser's PushManager.subscribe() needs the VAPID public key as a raw Uint8Array, not the
// base64url string the backend/env var gives us.
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(normalized);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

async function getRegistration(): Promise<ServiceWorkerRegistration> {
  await navigator.serviceWorker.register("/sw.js");
  // register() resolves once the registration exists, but the worker may still be
  // installing/waiting - pushManager needs an ACTIVE worker, so wait for that specifically.
  return navigator.serviceWorker.ready;
}

export async function getExistingSubscription(): Promise<PushSubscription | null> {
  if (!isPushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration("/sw.js");
  if (!registration) return null;
  return registration.pushManager.getSubscription();
}

/** Requests notification permission, subscribes via the browser's Push API, and registers the
 * subscription with the backend. Throws if permission is denied or push isn't supported. */
export async function subscribeToPush(): Promise<void> {
  if (!isPushSupported()) throw new Error("Web Push wird von diesem Browser nicht unterstützt.");

  const { public_key: publicKey, configured } = await pushApi.getVapidPublicKey();
  if (!configured || !publicKey) {
    throw new Error("Push ist auf diesem Server nicht konfiguriert (VAPID-Schlüssel fehlen).");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Benachrichtigungen wurden nicht erlaubt.");
  }

  const registration = await getRegistration();
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });

  await pushApi.subscribePush(subscription.toJSON() as PushSubscriptionJSON);
}

export async function unsubscribeFromPush(): Promise<void> {
  const subscription = await getExistingSubscription();
  if (!subscription) return;
  const endpoint = subscription.endpoint;
  await subscription.unsubscribe();
  await pushApi.unsubscribePush(endpoint);
}
