"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { PageHeader } from "@/components/PageHeader";
import { ApiError } from "@/lib/api-client";
import * as adminApi from "@/lib/api/admin";
import { useAuth } from "@/lib/auth-context";
import type { AppSettings, User } from "@/lib/types";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function AdminContent() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [pendingUsers, setPendingUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingRegistration, setSavingRegistration] = useState(false);
  const [savingPause, setSavingPause] = useState(false);
  const [pauseMessage, setPauseMessage] = useState("");
  const [decidingUserId, setDecidingUserId] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    const [settingsData, usersData, pendingData] = await Promise.all([
      adminApi.getSettings(),
      adminApi.listUsers(),
      adminApi.listPendingUsers(),
    ]);
    setSettings(settingsData);
    setPauseMessage(settingsData.system_paused_message ?? "");
    setUsers(usersData);
    setPendingUsers(pendingData);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadAll();
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadAll]);

  async function decide(userId: string, approvalStatus: "approved" | "declined") {
    setDecidingUserId(userId);
    setError(null);
    try {
      const stillPending = await adminApi.setUserApproval(userId, approvalStatus);
      setPendingUsers(stillPending);
      // The main "Nutzer"-list's approval_status badge also needs to reflect the decision.
      const refreshedUsers = await adminApi.listUsers();
      setUsers(refreshedUsers);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Aktion fehlgeschlagen.");
    } finally {
      setDecidingUserId(null);
    }
  }

  async function toggleRegistration() {
    if (!settings) return;
    setSavingRegistration(true);
    setError(null);
    try {
      const updated = await adminApi.updateSettings({ registration_open: !settings.registration_open });
      setSettings(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setSavingRegistration(false);
    }
  }

  async function handlePauseSubmit(e: FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setSavingPause(true);
    setError(null);
    try {
      const updated = await adminApi.updateSettings({
        system_paused: !settings.system_paused,
        system_paused_message: pauseMessage.trim() || null,
      });
      setSettings(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setSavingPause(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-zinc-500">Lade...</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <ErrorMessage message={error} />

      <section className="animate-fade-in-up rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
        <h2 className="mb-1 text-sm font-semibold text-zinc-700 dark:text-zinc-300">Registrierung</h2>
        <p className="mb-3 text-xs text-zinc-500">
          Wenn geschlossen, können sich keine neuen Nutzer mehr registrieren — bestehende Konten sind
          davon nicht betroffen.
        </p>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={settings?.registration_open ?? false}
            onChange={toggleRegistration}
            disabled={savingRegistration}
            className="h-5 w-5 cursor-pointer accent-indigo-500"
          />
          Neue Registrierungen erlauben
        </label>
      </section>

      <section
        style={{ animationDelay: "60ms" }}
        className="animate-fade-in-up rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800"
      >
        <h2 className="mb-1 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Ausstehende Registrierungen {pendingUsers.length > 0 ? `(${pendingUsers.length})` : ""}
        </h2>
        <p className="mb-3 text-xs text-zinc-500">
          Jede Registrierung (außer der allerersten, die automatisch Admin wird) muss hier erst
          freigegeben werden, bevor sich der Nutzer einloggen kann.
        </p>
        {pendingUsers.length === 0 ? (
          <p className="text-sm text-zinc-500">Keine offenen Registrierungen.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {pendingUsers.map((u, i) => (
              <li
                key={u.id}
                style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
                className="animate-fade-in-up flex items-center justify-between gap-3 rounded-xl border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
              >
                <div className="min-w-0">
                  <p className="truncate text-zinc-900 dark:text-zinc-100">{u.display_name}</p>
                  <p className="truncate text-xs text-zinc-500">{u.email}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => decide(u.id, "approved")}
                    disabled={decidingUserId === u.id}
                    className="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-all hover:scale-105 hover:bg-emerald-500 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
                  >
                    Annehmen
                  </button>
                  <button
                    type="button"
                    onClick={() => decide(u.id, "declined")}
                    disabled={decidingUserId === u.id}
                    className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-all hover:scale-105 hover:bg-red-50 hover:text-red-700 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-red-950/40"
                  >
                    Ablehnen
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        style={{ animationDelay: "90ms" }}
        className="animate-fade-in-up rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800"
      >
        <h2 className="mb-1 text-sm font-semibold text-zinc-700 dark:text-zinc-300">System pausieren</h2>
        <p className="mb-3 text-xs text-zinc-500">
          Blockiert nur Chat-/Voice-Anfragen an das LLM (z.B. für Wartung oder bei Überlast) — Login,
          Kalender, Home Assistant, Timer usw. bleiben normal erreichbar, auch für dich als Admin.
        </p>
        <form onSubmit={handlePauseSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Grund (optional, wird Nutzern angezeigt)"
            value={pauseMessage}
            onChange={(e) => setPauseMessage(e.target.value)}
            className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            type="submit"
            disabled={savingPause}
            className={`w-fit rounded-full px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] active:scale-95 disabled:opacity-50 disabled:hover:scale-100 ${
              settings?.system_paused
                ? "bg-emerald-600 hover:bg-emerald-500"
                : "bg-red-600 hover:bg-red-500"
            }`}
          >
            {settings?.system_paused ? "System wieder freigeben" : "System jetzt pausieren"}
          </button>
        </form>
      </section>

      <section
        style={{ animationDelay: "120ms" }}
        className="animate-fade-in-up rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800"
      >
        <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">Nutzer ({users.length})</h2>
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {users.map((u, i) => (
            <li
              key={u.id}
              style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
              className="animate-fade-in-up flex items-center justify-between rounded-lg px-1 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
            >
              <div>
                <p className="text-zinc-900 dark:text-zinc-100">
                  {u.display_name} {u.is_admin ? <span className="text-xs text-indigo-500">(Admin)</span> : null}
                </p>
                <p className="text-xs text-zinc-500">{u.email}</p>
              </div>
              <span className="text-xs text-zinc-400">seit {formatDate(u.created_at)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default function AdminPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user && !user.is_admin) {
      router.replace("/voice");
    }
  }, [isLoading, user, router]);

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4">
        <PageHeader title="Admin" />
        {isLoading || !user ? (
          <p className="text-sm text-zinc-500">Lade...</p>
        ) : !user.is_admin ? null : (
          <AdminContent />
        )}
      </div>
    </AppShell>
  );
}
