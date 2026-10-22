"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as authApi from "@/lib/api/auth";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Only shown once we actually know the server has SSO configured - most self-hosted
  // instances won't, and a button that just 404s would be confusing.
  const [ssoEnabled, setSsoEnabled] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/voice");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    authApi
      .ssoStatus()
      .then((status) => setSsoEnabled(status.enabled))
      .catch(() => setSsoEnabled(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/voice");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anmeldung fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center overflow-y-auto p-4">
      <div className="animate-scale-in w-full max-w-sm rounded-3xl border border-zinc-200 bg-white p-6 shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="mb-1 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Bei OwnAI anmelden
        </h1>
        <p className="mb-6 text-sm text-zinc-500">Dein persönlicher Assistent, auf deinem eigenen Server.</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700 dark:text-zinc-300">E-Mail</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700 dark:text-zinc-300">Passwort</span>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <ErrorMessage message={error} />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {submitting ? "Melde an..." : "Anmelden"}
          </button>
        </form>
        {ssoEnabled ? (
          <>
            <div className="my-4 flex items-center gap-3 text-xs text-zinc-400">
              <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
              oder
              <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
            </div>
            <a
              href={authApi.SSO_LOGIN_URL}
              className="flex items-center justify-center rounded-xl border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 transition-all hover:scale-[1.03] hover:bg-zinc-50 active:scale-95 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
            >
              Mit SSO anmelden
            </a>
          </>
        ) : null}
        <p className="mt-4 text-sm text-zinc-500">
          Noch kein Konto?{" "}
          <Link href="/register" className="font-medium text-zinc-900 underline dark:text-zinc-100">
            Registrieren
          </Link>
        </p>
      </div>
    </div>
  );
}
