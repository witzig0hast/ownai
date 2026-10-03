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

export async function listPendingUsers(): Promise<User[]> {
  const data = await apiFetch<{ users: User[] }>("/admin/users/pending");
  return data.users;
}

export async function setUserApproval(
  userId: string,
  approvalStatus: "approved" | "declined",
): Promise<User[]> {
  const data = await apiFetch<{ users: User[] }>(`/admin/users/${userId}/approval`, {
    method: "PATCH",
    body: { approval_status: approvalStatus },
  });
  return data.users;
}
