import { apiFetch } from "../api-client";

export interface VapidPublicKeyResponse {
  public_key: string | null;
  configured: boolean;
}

export function getVapidPublicKey(): Promise<VapidPublicKeyResponse> {
  return apiFetch<VapidPublicKeyResponse>("/push/vapid-public-key");
}

export function subscribePush(subscription: PushSubscriptionJSON): Promise<void> {
  return apiFetch<void>("/push/subscribe", {
    method: "POST",
    body: { endpoint: subscription.endpoint, keys: subscription.keys },
  });
}

export function unsubscribePush(endpoint: string): Promise<void> {
  return apiFetch<void>("/push/unsubscribe", {
    method: "POST",
    body: { endpoint },
  });
}
