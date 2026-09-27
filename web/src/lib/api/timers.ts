import { apiFetch } from "../api-client";
import type { Timer } from "../types";

export async function listTimers(): Promise<Timer[]> {
  const data = await apiFetch<{ timers: Timer[] }>("/timers");
  return data.timers;
}

export function cancelTimer(id: string): Promise<Timer> {
  return apiFetch<Timer>(`/timers/${id}/cancel`, { method: "POST" });
}
