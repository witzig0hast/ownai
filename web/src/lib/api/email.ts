import { apiFetch } from "../api-client";

export interface EmailCredentials {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  from_address: string;
  use_tls: boolean;
}

export function connectEmail(credentials: EmailCredentials): Promise<{ connected: true }> {
  return apiFetch<{ connected: true }>("/integrations/email", {
    method: "POST",
    body: credentials,
  });
}

export interface EmailStatus {
  has_custom_account: boolean;
  effective_from_address: string | null;
}

export function getEmailStatus(): Promise<EmailStatus> {
  return apiFetch<EmailStatus>("/integrations/email");
}
