import { apiFetch } from "../api-client";
import type { AgentLogEntry, AgentPreset, PermanentAgent } from "../types";

export async function listPresets(): Promise<AgentPreset[]> {
  const data = await apiFetch<{ presets: AgentPreset[] }>("/permanent-agents/presets");
  return data.presets;
}

export async function listAgents(): Promise<PermanentAgent[]> {
  const data = await apiFetch<{ agents: PermanentAgent[] }>("/permanent-agents");
  return data.agents;
}

export interface AgentWritePayload {
  name?: string;
  preset?: string;
  role_prompt?: string;
  interval_minutes?: number;
  active?: boolean;
}

export function createAgent(payload: AgentWritePayload): Promise<PermanentAgent> {
  return apiFetch<PermanentAgent>("/permanent-agents", { method: "POST", body: payload });
}

export function updateAgent(agentId: string, patch: AgentWritePayload): Promise<PermanentAgent> {
  return apiFetch<PermanentAgent>(`/permanent-agents/${agentId}`, { method: "PATCH", body: patch });
}

export function deleteAgent(agentId: string): Promise<void> {
  return apiFetch<void>(`/permanent-agents/${agentId}`, { method: "DELETE" });
}

export async function listLog(agentId: string, limit = 50): Promise<AgentLogEntry[]> {
  const data = await apiFetch<{ entries: AgentLogEntry[] }>(`/permanent-agents/${agentId}/log?limit=${limit}`);
  return data.entries;
}
