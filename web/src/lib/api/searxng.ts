import { apiFetch } from "../api-client";

export function connectSearxng(url: string): Promise<{ connected: true }> {
  return apiFetch<{ connected: true }>("/integrations/searxng", {
    method: "POST",
    body: { url },
  });
}

export interface SearxngStatus {
  connected: boolean;
  url: string | null;
}

export function getSearxngStatus(): Promise<SearxngStatus> {
  return apiFetch<SearxngStatus>("/integrations/searxng");
}
