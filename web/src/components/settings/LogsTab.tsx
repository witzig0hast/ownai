"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as logsApi from "@/lib/api/logs";
import type { LogEntry } from "@/lib/types";

const LEVELS: { key: string; label: string }[] = [
  { key: "", label: "Alle Stufen" },
  { key: "info", label: "Info" },
  { key: "warning", label: "Warnung" },
  { key: "error", label: "Fehler" },
];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("de-DE");
  } catch {
    return iso;
  }
}

function levelClasses(level: string): string {
  if (level === "error") return "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400";
  if (level === "warning") return "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-400";
  return "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400";
}

export function LogsTab() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState("");
  const [level, setLevel] = useState("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await logsApi.listLogs({
        category: category || undefined,
        level: level || undefined,
        q: q.trim() || undefined,
      });
      setLogs(result.logs);
      setCategories(result.categories);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Logs konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [category, level, q]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  return (
    <div className="max-w-2xl">
      <p className="mb-4 text-sm text-zinc-500">
        Hier siehst du, was im Hintergrund passiert ist — z.B. &bdquo;E-Mail&ldquo; auswählen, um alle
        E-Mail-Logs zu sehen und nachzuvollziehen, was dabei schiefgegangen ist.
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        >
          <option value="">Alle Kategorien</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        >
          {LEVELS.map((l) => (
            <option key={l.key} value={l.key}>
              {l.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Suchen..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="min-w-[10rem] flex-1 rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
      </div>

      <ErrorMessage message={error} />

      {loading ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-zinc-500">Keine Logs gefunden.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {logs.map((entry) => (
            <li
              key={entry.id}
              className="animate-fade-in-up rounded-2xl border border-zinc-200 p-3 text-sm dark:border-zinc-800"
            >
              <button
                type="button"
                onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
                className="flex w-full items-start justify-between gap-3 text-left"
                disabled={!entry.detail}
              >
                <div className="min-w-0">
                  <div className="mb-1 flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${levelClasses(entry.level)}`}>
                      {entry.level}
                    </span>
                    <span className="text-xs text-zinc-400">{entry.category}</span>
                  </div>
                  <p className="text-zinc-900 dark:text-zinc-100">{entry.message}</p>
                </div>
                <span className="shrink-0 text-xs text-zinc-400">{formatDate(entry.created_at)}</span>
              </button>
              {expandedId === entry.id && entry.detail && (
                <pre className="mt-2 overflow-x-auto rounded-xl bg-zinc-50 p-2 text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
                  {entry.detail}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
