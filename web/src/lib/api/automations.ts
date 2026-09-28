import { apiFetch } from "../api-client";
import type { Automation } from "../types";

export interface AutomationWritePayload {
  entity_id?: string;
  trigger_state?: string;
  message?: string;
  active?: boolean;
}

export async function listAutomations(): Promise<Automation[]> {
  const data = await apiFetch<{ automations: Automation[] }>("/automations");
  return data.automations;
}

export function createAutomation(payload: AutomationWritePayload): Promise<Automation> {
  return apiFetch<Automation>("/automations", { method: "POST", body: payload });
}

export function updateAutomation(automationId: string, patch: AutomationWritePayload): Promise<Automation> {
  return apiFetch<Automation>(`/automations/${automationId}`, { method: "PATCH", body: patch });
}

export function deleteAutomation(automationId: string): Promise<void> {
  return apiFetch<void>(`/automations/${automationId}`, { method: "DELETE" });
}
