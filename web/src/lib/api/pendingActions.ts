import { apiFetch } from "../api-client";
import type { PendingAction } from "../types";

export async function listPendingActions(): Promise<PendingAction[]> {
  const data = await apiFetch<{ pending_actions: PendingAction[] }>("/pending-actions");
  return data.pending_actions;
}

export function approvePendingAction(id: string): Promise<PendingAction> {
  return apiFetch<PendingAction>(`/pending-actions/${id}/approve`, { method: "POST" });
}

export function declinePendingAction(id: string): Promise<PendingAction> {
  return apiFetch<PendingAction>(`/pending-actions/${id}/decline`, { method: "POST" });
}
