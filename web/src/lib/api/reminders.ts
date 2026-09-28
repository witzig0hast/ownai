import { apiFetch } from "../api-client";
import type { Reminder, ReminderRecurrence, Weekday } from "../types";

export interface ReminderWritePayload {
  label?: string;
  recurrence?: ReminderRecurrence;
  hour?: number;
  minute?: number;
  weekday?: Weekday | null;
  day_of_month?: number | null;
  active?: boolean;
}

export async function listReminders(): Promise<Reminder[]> {
  const data = await apiFetch<{ reminders: Reminder[] }>("/reminders");
  return data.reminders;
}

export function createReminder(payload: ReminderWritePayload): Promise<Reminder> {
  return apiFetch<Reminder>("/reminders", { method: "POST", body: payload });
}

export function updateReminder(reminderId: string, patch: ReminderWritePayload): Promise<Reminder> {
  return apiFetch<Reminder>(`/reminders/${reminderId}`, { method: "PATCH", body: patch });
}

export function deleteReminder(reminderId: string): Promise<void> {
  return apiFetch<void>(`/reminders/${reminderId}`, { method: "DELETE" });
}
