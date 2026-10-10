import { apiFetch } from "../api-client";
import { API_BASE_URL } from "../config";
import type { AuthTokens, User } from "../types";

export function register(email: string, password: string, displayName: string): Promise<User> {
  return apiFetch<User>("/auth/register", {
    method: "POST",
    skipAuth: true,
    body: { email, password, display_name: displayName },
  });
}

export function login(email: string, password: string): Promise<AuthTokens> {
  return apiFetch<AuthTokens>("/auth/login", {
    method: "POST",
    skipAuth: true,
    body: { email, password },
  });
}

export function me(): Promise<User> {
  return apiFetch<User>("/users/me");
}

export function ssoStatus(): Promise<{ enabled: boolean }> {
  return apiFetch<{ enabled: boolean }>("/auth/sso/status", { skipAuth: true });
}

// Full-page navigation target, not a fetch() call - the backend 307-redirects the browser
// itself to the SSO provider's own login page (see app/api/sso.py).
export const SSO_LOGIN_URL = `${API_BASE_URL}/auth/sso/login`;
