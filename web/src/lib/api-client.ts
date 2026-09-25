import { API_BASE_URL } from "./config";
import { clearTokens, getTokens, setTokens } from "./auth-storage";
import type { ApiErrorBody, AuthTokens } from "./types";

/** Error thrown for every non-2xx response, carrying the backend's error envelope. */
export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  /** JSON-serializable request body. Stringified automatically. */
  body?: unknown;
  /** Skip attaching the Authorization header and skip the refresh-on-401 flow (used for /auth/*). */
  skipAuth?: boolean;
}

// Ensures at most one refresh request is in flight, even if several API
// calls hit a 401 at the same time.
let inFlightRefresh: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getTokens();
  if (!tokens) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refreshToken }),
    });
    if (!res.ok) {
      clearTokens();
      return null;
    }
    const data = (await res.json()) as AuthTokens;
    setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

async function parseErrorBody(res: Response): Promise<{ code: string; message: string }> {
  try {
    const data = (await res.json()) as ApiErrorBody;
    if (data?.error?.code && data?.error?.message) {
      return { code: data.error.code, message: data.error.message };
    }
  } catch {
    // response wasn't JSON - fall through to the generic message below
  }
  return { code: "unknown_error", message: `Request failed with status ${res.status}` };
}

/**
 * Calls the OwnAI backend API (see /API.md). Automatically attaches the
 * bearer access token, retries once with a refreshed token on a 401, and
 * throws an ApiError with the backend's `{ code, message }` on failure.
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { skipAuth, body, headers, ...rest } = options;

  const buildInit = (accessToken: string | null): RequestInit => {
    const finalHeaders = new Headers(headers);
    finalHeaders.set("Content-Type", "application/json");
    if (accessToken && !skipAuth) {
      finalHeaders.set("Authorization", `Bearer ${accessToken}`);
    }
    return {
      ...rest,
      headers: finalHeaders,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    };
  };

  const tokens = getTokens();
  let res = await fetch(`${API_BASE_URL}${path}`, buildInit(tokens?.accessToken ?? null));

  if (res.status === 401 && !skipAuth) {
    if (!inFlightRefresh) {
      inFlightRefresh = refreshAccessToken().finally(() => {
        inFlightRefresh = null;
      });
    }
    const newAccessToken = await inFlightRefresh;

    if (!newAccessToken) {
      clearTokens();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        // Full navigation is intentional here: this module runs outside
        // React, so a router instance isn't available, and a hard
        // redirect correctly drops any stale in-memory state.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = "/login";
      }
      throw new ApiError("unauthorized", "Session expired. Please log in again.", 401);
    }

    res = await fetch(`${API_BASE_URL}${path}`, buildInit(newAccessToken));
  }

  if (!res.ok) {
    const { code, message } = await parseErrorBody(res);
    throw new ApiError(code, message, res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}
