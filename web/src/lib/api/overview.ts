import { apiFetch } from "../api-client";
import type { Weather } from "../types";

export interface OverviewEvent {
  title: string;
  start: string;
  end: string;
  location: string | null;
  all_day: boolean;
}

export interface OverviewList {
  id: string;
  name: string;
  kind: "todo" | "shopping";
  open_count: number;
  open_items: { id: string; content: string }[];
}

export interface Overview {
  display_name: string;
  today: string;
  calendar: { connected: boolean; events: OverviewEvent[]; error: string | null };
  lists: OverviewList[];
  reminders: { id: string; label: string; next_at: string }[];
  birthdays: { contact_id: string; name: string; date: string; days_until: number; turns: number | null }[];
  expenses: { month_total: number; count: number; by_category: { category: string; total: number }[] };
  weather: { home_city: string | null; data: Weather | null; error: string | null };
  pending_actions: number;
}

export function getOverview(): Promise<Overview> {
  return apiFetch<Overview>("/overview");
}

export async function getBriefing(): Promise<string> {
  const data = await apiFetch<{ text: string }>("/overview/briefing");
  return data.text;
}
