"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "./api/auth";
import { clearTokens, getTokens, getUser, setTokens, setUser as persistUser } from "./auth-storage";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  /** True while the initial session check (on page load) is running. */
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
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
      } catch {
        if (cancelled) return;
        clearTokens();
        setUserState(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await authApi.login(email, password);
    setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
    const freshUser = await authApi.me();
    setUserState(freshUser);
    persistUser(freshUser);
  }, []);

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
      value={{ user, isLoading, isAuthenticated: user !== null, login, register, logout }}
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
