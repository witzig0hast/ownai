"use client";

import { useEffect, useState, type FormEvent } from "react";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingRegistration, setSavingRegistration] = useState(false);
  const [savingPause, setSavingPause] = useState(false);
  const [pauseMessage, setPauseMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [settingsData, usersData] = await Promise.all([adminApi.getSettings(), adminApi.listUsers()]);
        if (cancelled) return;
        setSettings(settingsData);
        setPauseMessage(settingsData.system_paused_message ?? "");
        setUsers(usersData);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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

      <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
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
            className="h-4 w-4"
          />
          Neue Registrierungen erlauben
        </label>
      </section>

      <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
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
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
          <button
            type="submit"
            disabled={savingPause}
            className={`w-fit rounded-md px-3 py-2 text-sm font-medium text-white transition-colors disabled:opacity-50 ${
              settings?.system_paused
                ? "bg-emerald-600 hover:bg-emerald-500"
                : "bg-red-600 hover:bg-red-500"
            }`}
          >
            {settings?.system_paused ? "System wieder freigeben" : "System jetzt pausieren"}
          </button>
        </form>
      </section>

      <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">Nutzer ({users.length})</h2>
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {users.map((u) => (
            <li key={u.id} className="flex items-center justify-between py-2 text-sm">
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
