import { apiFetch } from "../api-client";
import type { LogEntry } from "../types";

export interface LogsFilter {
  category?: string;
  level?: string;
  q?: string;
}

export async function listLogs(filter: LogsFilter = {}): Promise<{ logs: LogEntry[]; categories: string[] }> {
  const params = new URLSearchParams();
  if (filter.category) params.set("category", filter.category);
  if (filter.level) params.set("level", filter.level);
  if (filter.q) params.set("q", filter.q);
  const query = params.toString();
  return apiFetch<{ logs: LogEntry[]; categories: string[] }>(`/logs${query ? `?${query}` : ""}`);
}
