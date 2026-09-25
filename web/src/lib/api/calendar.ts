import { apiFetch } from "../api-client";
import type { CalendarEvent } from "../types";

export interface CaldavCredentials {
  url: string;
  username: string;
  password: string;
}

export function connectCaldav(credentials: CaldavCredentials): Promise<{ connected: true }> {
  return apiFetch<{ connected: true }>("/integrations/caldav", {
    method: "POST",
    body: credentials,
  });
}

/** start/end are ISO-8601 date (or datetime) strings, per /API.md. */
export async function listEvents(start: string, end: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams({ start, end });
  const data = await apiFetch<{ events: CalendarEvent[] }>(`/calendar/events?${params.toString()}`);
  return data.events;
}

export interface CreateEventInput {
  title: string;
  start: string;
  end: string;
  location: string | null;
}

export function createEvent(input: CreateEventInput): Promise<CalendarEvent> {
  return apiFetch<CalendarEvent>("/calendar/events", {
    method: "POST",
    body: input,
  });
}
