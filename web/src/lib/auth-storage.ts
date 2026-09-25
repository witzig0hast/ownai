// Thin, SSR-safe wrapper around localStorage for auth state.
//
// Trade-off (see README.md "Auth storage" section for the full writeup):
// we store the access + refresh tokens in localStorage rather than
// httpOnly cookies behind a proxy. That's simpler (no Next.js API routes
// re-implementing every backend endpoint) and is an accepted trade-off for
// a single-user, self-hosted personal tool. It does mean tokens are
// readable by any JS running on the page (XSS risk).

import type { User } from "./types";

const ACCESS_TOKEN_KEY = "ownai.access_token";
const REFRESH_TOKEN_KEY = "ownai.refresh_token";
const USER_KEY = "ownai.user";

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getTokens(): StoredTokens | null {
  if (!isBrowser()) return null;
  try {
    const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!accessToken || !refreshToken) return null;
    return { accessToken, refreshToken };
  } catch {
    return null;
  }
}

export function setTokens(tokens: StoredTokens): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  } catch {
    // localStorage unavailable (private mode, quota, etc.) - ignore.
  }
}

export function clearTokens(): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    // ignore
  }
}

export function getUser(): User | null {
  if (!isBrowser()) return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function setUser(user: User): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // ignore
  }
}
