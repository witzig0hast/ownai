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

export interface DependencyStatus {
  key: string;
  label: string;
  status: "ok" | "error" | "not_configured";
  detail: string | null;
  optional: boolean;
  latency_ms: number | null;
}

export async function getSystemStatus(): Promise<DependencyStatus[]> {
  const data = await apiFetch<{ dependencies: DependencyStatus[] }>("/admin/system-status");
  return data.dependencies;
}
