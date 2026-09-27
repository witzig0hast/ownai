import { apiFetch } from "../api-client";
import type { Memory } from "../types";

export async function listMemories(): Promise<Memory[]> {
  const data = await apiFetch<{ memories: Memory[] }>("/memory");
  return data.memories;
}

export function createMemory(content: string): Promise<Memory> {
  return apiFetch<Memory>("/memory", { method: "POST", body: { content } });
}

export function deleteMemory(memoryId: string): Promise<void> {
  return apiFetch<void>(`/memory/${memoryId}`, { method: "DELETE" });
}
