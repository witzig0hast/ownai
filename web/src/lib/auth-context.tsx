"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { ApiError } from "./api-client";
import * as authApi from "./api/auth";
import { clearTokens, getTokens, getUser, setTokens, setUser as persistUser } from "./auth-storage";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  /** True while the initial session check (on page load) is running. */
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  /** Stores an already-issued token pair (e.g. from the SSO callback page, see
   * app/sso-callback/page.tsx) and loads the profile - the shared second half of login(). */
  loginWithTokens: (accessToken: string, refreshToken: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  /** Re-fetches /users/me and updates the cached profile - for a change made via another
   * endpoint (e.g. linking/unlinking SSO in AccountTab.tsx) that the backend doesn't return a
   * fresh User for itself. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const tokens = getTokens();
      if (!tokens) {
        setIsLoading(false);
        return;
      }
      // Show the cached profile immediately, then confirm/refresh it against the API.
      const cachedUser = getUser();
      if (cachedUser) setUserState(cachedUser);

      try {
        const freshUser = await authApi.me();
        if (cancelled) return;
        setUserState(freshUser);
        persistUser(freshUser);
      } catch (err) {
        if (cancelled) return;
        // Only a real "not authenticated" ends the session (apiFetch has already tried a refresh
        // by then). No signal, the backend restarting, or this request being cut off by a quick
        // navigation used to log the user out here; now the cached profile simply stays.
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          setUserState(null);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const loginWithTokens = useCallback(async (accessToken: string, refreshToken: string) => {
    setTokens({ accessToken, refreshToken });
    const freshUser = await authApi.me();
    setUserState(freshUser);
    persistUser(freshUser);
  }, []);

  const refreshUser = useCallback(async () => {
    const freshUser = await authApi.me();
    setUserState(freshUser);
    persistUser(freshUser);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authApi.login(email, password);
      await loginWithTokens(tokens.access_token, tokens.refresh_token);
    },
    [loginWithTokens],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      await authApi.register(email, password, displayName);
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    clearTokens();
    setUserState(null);
    if (typeof window !== "undefined") {
      // Full navigation (not router.push) is intentional: it drops all
      // in-memory app state after logout instead of leaving stale data
      // rendered behind the redirect.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        loginWithTokens,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
