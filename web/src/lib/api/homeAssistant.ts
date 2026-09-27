import { apiFetch } from "../api-client";

export interface HomeAssistantCredentials {
  url: string;
  token: string;
}

export function connectHomeAssistant(
  credentials: HomeAssistantCredentials,
): Promise<{ connected: true }> {
  return apiFetch<{ connected: true }>("/integrations/home-assistant", {
    method: "POST",
    body: credentials,
  });
}

export interface HomeAssistantEntity {
  entity_id: string;
  domain: string;
  state: string | null;
  friendly_name: string;
}

export async function listEntities(domain?: string): Promise<HomeAssistantEntity[]> {
  const query = domain ? `?domain=${encodeURIComponent(domain)}` : "";
  const data = await apiFetch<{ entities: HomeAssistantEntity[] }>(`/home-assistant/entities${query}`);
  return data.entities;
}
