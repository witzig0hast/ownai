import { apiFetch } from "../api-client";

export interface SetupItem {
  key: string;
  title: string;
  description: string;
  settings_tab: string | null;
  href: string | null;
  done: boolean;
}

export interface SetupStatus {
  items: SetupItem[];
  completed: number;
  total: number;
  dismissed: boolean;
}

export function getSetupStatus(): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/users/me/setup-status");
}

export function setSetupDismissed(dismissed: boolean): Promise<SetupStatus> {
  return apiFetch<SetupStatus>("/users/me/setup-status", { method: "PUT", body: { dismissed } });
}
