"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import { getSystemStatus, type DependencyStatus } from "@/lib/api/admin";

const STATUS_STYLE: Record<DependencyStatus["status"], { dot: string; label: string }> = {
  ok: { dot: "bg-emerald-500", label: "OK" },
  error: { dot: "bg-red-500", label: "Fehler" },
  not_configured: { dot: "bg-zinc-300 dark:bg-zinc-600", label: "Nicht eingerichtet" },
};

export function SystemStatusCard() {
  const [deps, setDeps] = useState<DependencyStatus[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDeps(await getSystemStatus());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Status konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await refresh();
    })();
  }, [refresh]);

  const criticalDown = deps?.filter((d) => d.status === "error" && !d.optional) ?? [];

  return (
    <section className="animate-fade-in-up rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
      <div className="mb-1 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Systemstatus</h2>
        <button
          type="button"
          onClick={refresh}
          disabled={loading}
          className="rounded-full border border-zinc-300 px-3 py-1 text-xs font-medium text-zinc-700 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:border-zinc-700 dark:text-zinc-300"
        >
          {loading ? "Prüfe..." : "Neu prüfen"}
        </button>
      </div>
      <p className="mb-3 text-xs text-zinc-500">
        Prüft live, ob alles erreichbar ist, wovon OwnAI abhängt. Rot bei einem Pflicht-Baustein heißt:
        der Assistent funktioniert gerade nicht richtig.
      </p>
      <ErrorMessage message={error} />

      {criticalDown.length > 0 ? (
        <p className="mb-3 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
          {criticalDown.map((d) => d.label).join(", ")} nicht erreichbar — Chat/Voice werden fehlschlagen.
        </p>
      ) : null}

      {deps === null ? (
        loading ? <p className="text-sm text-zinc-500">Prüfe...</p> : null
      ) : (
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {deps.map((d) => {
            const style = STATUS_STYLE[d.status];
            return (
              <li key={d.key} className="flex items-start justify-between gap-3 py-2 text-sm">
                <div className="flex min-w-0 items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${style.dot}`} aria-hidden />
                  <div className="min-w-0">
                    <p className="text-zinc-900 dark:text-zinc-100">
                      {d.label}
                      {d.optional ? <span className="ml-1 text-xs text-zinc-400">(optional)</span> : null}
                    </p>
                    {d.detail ? <p className="break-words text-xs text-zinc-500">{d.detail}</p> : null}
                  </div>
                </div>
                <span className="shrink-0 text-xs text-zinc-500">
                  {style.label}
                  {d.latency_ms !== null ? ` · ${d.latency_ms} ms` : ""}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
