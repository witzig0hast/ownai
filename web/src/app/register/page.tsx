"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const { register, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Every account after the very first needs an admin to approve it before it can log in
  // (DECISIONS.md #13) - register() succeeds, then its automatic login is refused with
  // registration_pending. That's the expected outcome, not an error, so it gets its own screen.
  const [awaitingApproval, setAwaitingApproval] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/voice");
    }
  }, [isLoading, isAuthenticated, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Das Passwort muss mindestens 8 Zeichen lang sein.");
      return;
    }

    setSubmitting(true);
    try {
      await register(email, password, displayName);
      router.replace("/voice");
    } catch (err) {
      if (err instanceof ApiError && err.code === "registration_pending") {
        setAwaitingApproval(true);
        return;
      }
      setError(err instanceof ApiError ? err.message : "Registrierung fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setSubmitting(false);
    }
  }

  if (awaitingApproval) {
    return (
      <div className="flex flex-1 items-center justify-center overflow-y-auto p-4">
        <div className="animate-scale-in w-full max-w-sm rounded-3xl border border-zinc-200 bg-white p-6 text-center shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
          <h1 className="mb-2 text-xl font-semibold text-zinc-900 dark:text-zinc-100">Registrierung eingegangen</h1>
          <p className="mb-5 text-sm text-zinc-500">
            Ein Admin muss dein Konto noch freischalten. Danach kannst du dich mit {email} und deinem
            Passwort anmelden.
          </p>
          <Link href="/login" className="text-sm font-medium text-zinc-900 underline dark:text-zinc-100">
            Zum Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center overflow-y-auto p-4">
      <div className="animate-scale-in w-full max-w-sm rounded-3xl border border-zinc-200 bg-white p-6 shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="mb-1 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          OwnAI-Konto erstellen
        </h1>
        <p className="mb-6 text-sm text-zinc-500">Läuft komplett auf deinem eigenen Server.</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-zinc-700 dark:text-zinc-300">Name</span>
            <input
              type="text"
              required
              autoComplete="name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
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
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
            />
            <span className="text-xs text-zinc-400">Mindestens 8 Zeichen.</span>
          </label>
          <ErrorMessage message={error} />
          <button
            type="submit"
            disabled={submitting}
            className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {submitting ? "Erstelle Konto..." : "Konto erstellen"}
          </button>
        </form>
        <p className="mt-4 text-sm text-zinc-500">
          Schon ein Konto?{" "}
          <Link href="/login" className="font-medium text-zinc-900 underline dark:text-zinc-100">
            Anmelden
          </Link>
        </p>
      </div>
    </div>
  );
}
