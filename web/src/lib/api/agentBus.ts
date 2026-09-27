import { apiFetch } from "../api-client";
import type { AgentIdentity, AgentMessage } from "../types";

export async function listAgents(): Promise<AgentIdentity[]> {
  const data = await apiFetch<{ agents: AgentIdentity[] }>("/agent-bus/agents");
  return data.agents;
}

export interface AgentCreateResponse extends AgentIdentity {
  api_key: string;
}

export function registerAgent(name: string, description: string | null): Promise<AgentCreateResponse> {
  return apiFetch<AgentCreateResponse>("/agent-bus/agents", {
    method: "POST",
    body: { name, description },
  });
}

export function deleteAgent(agentId: string): Promise<void> {
  return apiFetch<void>(`/agent-bus/agents/${agentId}`, { method: "DELETE" });
}

export async function listMessages(): Promise<AgentMessage[]> {
  const data = await apiFetch<{ messages: AgentMessage[] }>("/agent-bus/messages");
  return data.messages;
}
