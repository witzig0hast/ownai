import { apiFetch } from "../api-client";
import type { AppSettings, User } from "../types";

export function getSettings(): Promise<AppSettings> {
  return apiFetch<AppSettings>("/admin/settings");
}

export function updateSettings(patch: Partial<AppSettings>): Promise<AppSettings> {
  return apiFetch<AppSettings>("/admin/settings", {
    method: "PATCH",
    body: patch,
  });
}

export async function listUsers(): Promise<User[]> {
  const data = await apiFetch<{ users: User[] }>("/admin/users");
  return data.users;
}
