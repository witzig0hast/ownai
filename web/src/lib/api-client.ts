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
  /** JSON-serializable request body (stringified automatically), or a FormData instance for
   * multipart/form-data uploads (sent as-is; the browser sets the correct Content-Type/boundary). */
  body?: unknown;
  /** Skip attaching the Authorization header and skip the refresh-on-401 flow (used for /auth/*). */
  skipAuth?: boolean;
}

// "unreachable" (no network, backend restarting, request aborted by a navigation) must NOT end
// the session - only the server actually rejecting the refresh token does. Treating every
// failure as "logged out" signed phone users out whenever they opened the app without signal.
type RefreshOutcome = { accessToken: string } | "rejected" | "unreachable";

// Ensures at most one refresh request is in flight, even if several API
// calls hit a 401 at the same time.
let inFlightRefresh: Promise<RefreshOutcome> | null = null;

async function refreshAccessToken(): Promise<RefreshOutcome> {
  const tokens = getTokens();
  if (!tokens) return "rejected";

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refreshToken }),
    });
  } catch {
    return "unreachable";
  }
  if (res.status >= 500) return "unreachable";
  if (!res.ok) {
    clearTokens();
    return "rejected";
  }
  const data = (await res.json()) as AuthTokens;
  setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });
  return { accessToken: data.access_token };
}

function sharedRefresh(): Promise<RefreshOutcome> {
  if (!inFlightRefresh) {
    inFlightRefresh = refreshAccessToken().finally(() => {
      inFlightRefresh = null;
    });
  }
  return inFlightRefresh;
}

export const NETWORK_ERROR_CODE = "network_error";

function unreachableError(): ApiError {
  return new ApiError(NETWORK_ERROR_CODE, "Server gerade nicht erreichbar - bitte gleich nochmal versuchen.", 0);
}

async function fetchOrThrow(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (err) {
    // An abort is the caller's own doing (e.g. search-as-you-type) - pass it through as is.
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw unreachableError();
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

  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

  const buildInit = (accessToken: string | null): RequestInit => {
    const finalHeaders = new Headers(headers);
    if (!isFormData) {
      // For FormData, leave Content-Type unset — the browser fills in
      // "multipart/form-data; boundary=..." itself, which we can't replicate manually.
      finalHeaders.set("Content-Type", "application/json");
    }
    if (accessToken && !skipAuth) {
      finalHeaders.set("Authorization", `Bearer ${accessToken}`);
    }
    return {
      ...rest,
      headers: finalHeaders,
      body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    };
  };

  const tokens = getTokens();
  let res = await fetchOrThrow(`${API_BASE_URL}${path}`, buildInit(tokens?.accessToken ?? null));

  if (res.status === 401 && !skipAuth) {
    const outcome = await sharedRefresh();
    if (outcome === "unreachable") throw unreachableError();
    if (outcome === "rejected") {
      clearTokens();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        // Full navigation is intentional here: this module runs outside
        // React, so a router instance isn't available, and a hard
        // redirect correctly drops any stale in-memory state.
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = "/login";
      }
      throw new ApiError("unauthorized", "Sitzung abgelaufen - bitte neu anmelden.", 401);
    }

    res = await fetchOrThrow(`${API_BASE_URL}${path}`, buildInit(outcome.accessToken));
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

/**
 * Like apiFetch, but for endpoints that return a raw file body (e.g. a generated PDF, or
 * synthesized audio) rather than JSON. GET by default; pass a JSON-serializable `body` for a
 * POST (e.g. TTS synthesis). Returns null for a 204 (e.g. nothing to synthesize).
 */
export async function apiFetchBlob(path: string, body?: unknown): Promise<Blob | null> {
  const buildInit = (accessToken: string | null): RequestInit => {
    const headers = new Headers();
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    if (body === undefined) return { headers };
    headers.set("Content-Type", "application/json");
    return { method: "POST", headers, body: JSON.stringify(body) };
  };

  const tokens = getTokens();
  let res = await fetchOrThrow(`${API_BASE_URL}${path}`, buildInit(tokens?.accessToken ?? null));

  if (res.status === 401) {
    const outcome = await sharedRefresh();
    if (outcome === "unreachable") throw unreachableError();
    if (outcome === "rejected") {
      clearTokens();
      throw new ApiError("unauthorized", "Sitzung abgelaufen - bitte neu anmelden.", 401);
    }
    res = await fetchOrThrow(`${API_BASE_URL}${path}`, buildInit(outcome.accessToken));
  }

  if (!res.ok) {
    const { code, message } = await parseErrorBody(res);
    throw new ApiError(code, message, res.status);
  }
  if (res.status === 204) return null;
  return await res.blob();
}
