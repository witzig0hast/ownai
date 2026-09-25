import { apiFetch } from "../api-client";
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
