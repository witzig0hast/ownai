import { apiFetch } from "../api-client";
import type { Contact } from "../types";

export interface ContactWritePayload {
  name?: string;
  phone?: string | null;
  email?: string | null;
  birthday_month?: number | null;
  birthday_day?: number | null;
  birthday_year?: number | null;
  notes?: string | null;
}

export async function listContacts(): Promise<Contact[]> {
  const data = await apiFetch<{ contacts: Contact[] }>("/contacts");
  return data.contacts;
}

export function createContact(payload: ContactWritePayload): Promise<Contact> {
  return apiFetch<Contact>("/contacts", { method: "POST", body: payload });
}

export function updateContact(contactId: string, patch: ContactWritePayload): Promise<Contact> {
  return apiFetch<Contact>(`/contacts/${contactId}`, { method: "PATCH", body: patch });
}

export function deleteContact(contactId: string): Promise<void> {
  return apiFetch<void>(`/contacts/${contactId}`, { method: "DELETE" });
}
