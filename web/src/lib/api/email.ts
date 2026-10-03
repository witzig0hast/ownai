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
  has_imap_account: boolean;
  inbound_agent_enabled: boolean;
}

export function getEmailStatus(): Promise<EmailStatus> {
  return apiFetch<EmailStatus>("/integrations/email");
}

export interface ImapCredentials {
  imap_host: string;
  imap_port: number;
  imap_username: string;
  imap_password: string;
}

export function connectImap(credentials: ImapCredentials): Promise<{ connected: true }> {
  return apiFetch<{ connected: true }>("/integrations/email/imap", {
    method: "POST",
    body: credentials,
  });
}

export function setInboundAgentEnabled(enabled: boolean): Promise<EmailStatus> {
  return apiFetch<EmailStatus>("/integrations/email/inbound-agent", {
    method: "PATCH",
    body: { enabled },
  });
}
