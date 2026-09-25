"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as suggestionsApi from "@/lib/api/suggestions";
import type { Suggestion } from "@/lib/types";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function SuggestionPayload({ payload }: { payload: Record<string, unknown> }) {
  const entries = Object.entries(payload);
  if (entries.length === 0) return null;
  return (
    <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-zinc-500">
      {entries.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="font-medium text-zinc-400">{key}</dt>
          <dd className="truncate">{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function SuggestionsPage() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    suggestionsApi
      .listSuggestions("open")
      .then((list) => {
        if (!cancelled) setSuggestions(list);
      })
      .catch((err) => {
        if (!cancelled) {
          setListError(err instanceof ApiError ? err.message : "Failed to load suggestions.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleApply(id: string) {
    setActionError(null);
    setPendingId(id);
    try {
      await suggestionsApi.applySuggestion(id);
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to apply suggestion.");
    } finally {
      setPendingId(null);
    }
  }

  async function handleDismiss(id: string) {
    setActionError(null);
    setPendingId(id);
    try {
      await suggestionsApi.dismissSuggestion(id);
      setSuggestions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Failed to dismiss suggestion.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-2xl flex-1 overflow-y-auto p-4">
        <h1 className="mb-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Suggestions
        </h1>
        <p className="mb-4 text-sm text-zinc-500">
          Generated from your Android notifications — review, apply or dismiss.
        </p>

        <ErrorMessage message={listError} />
        <div className="mb-3">
          <ErrorMessage message={actionError} />
        </div>

        {loading ? (
          <p className="text-sm text-zinc-500">Loading...</p>
        ) : suggestions.length === 0 ? (
          <p className="text-sm text-zinc-500">No open suggestions right now.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {suggestions.map((s) => (
              <li
                key={s.id}
                className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="mb-1 inline-block rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                      {s.kind === "calendar_event" ? "Calendar event" : "Reply draft"}
                    </span>
                    <p className="text-sm text-zinc-900 dark:text-zinc-100">{s.summary}</p>
                    <p className="mt-1 text-xs text-zinc-400">{formatTime(s.created_at)}</p>
                    <SuggestionPayload payload={s.payload} />
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => handleApply(s.id)}
                      disabled={pendingId === s.id}
                      className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
                    >
                      Apply
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDismiss(s.id)}
                      disabled={pendingId === s.id}
                      className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
