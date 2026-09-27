"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { PageHeader } from "@/components/PageHeader";
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

function formatDateTime(iso: unknown): string {
  if (typeof iso !== "string") return String(iso);
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

/**
 * Payload shape depends on `kind` (see API.md): calendar_event -> {title, start, end},
 * reply_draft -> {reply}. Showing it formatted per kind instead of a raw key/value dump.
 */
function SuggestionDetails({ suggestion }: { suggestion: Suggestion }) {
  if (suggestion.kind === "calendar_event") {
    const { title, start, end } = suggestion.payload as { title?: unknown; start?: unknown; end?: unknown };
    return (
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-zinc-500">
        {title ? (
          <>
            <dt className="font-medium text-zinc-400">Titel</dt>
            <dd className="truncate text-zinc-700 dark:text-zinc-300">{String(title)}</dd>
          </>
        ) : null}
        {start ? (
          <>
            <dt className="font-medium text-zinc-400">Start</dt>
            <dd className="text-zinc-700 dark:text-zinc-300">{formatDateTime(start)}</dd>
          </>
        ) : null}
        {end ? (
          <>
            <dt className="font-medium text-zinc-400">Ende</dt>
            <dd className="text-zinc-700 dark:text-zinc-300">{formatDateTime(end)}</dd>
          </>
        ) : null}
      </dl>
    );
  }

  if (suggestion.kind === "reply_draft") {
    const { reply } = suggestion.payload as { reply?: unknown };
    if (!reply) return null;
    return (
      <blockquote className="mt-2 border-l-2 border-zinc-300 pl-3 text-sm text-zinc-700 italic dark:border-zinc-700 dark:text-zinc-300">
        {String(reply)}
      </blockquote>
    );
  }

  return null;
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
          setListError(err instanceof ApiError ? err.message : "Vorschläge konnten nicht geladen werden.");
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
      setActionError(err instanceof ApiError ? err.message : "Vorschlag konnte nicht übernommen werden.");
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
      setActionError(err instanceof ApiError ? err.message : "Vorschlag konnte nicht verworfen werden.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-2xl flex-1 overflow-y-auto p-4">
        <PageHeader
          title="Vorschläge"
          subtitle={
            'Wenn die Android-App eine Benachrichtigung (z. B. WhatsApp) liest und OwnAI darin etwas ' +
            'Sinnvolles erkennt — einen Termin oder eine passende Antwort — taucht hier ein Vorschlag ' +
            'auf. „Übernehmen“ führt die Aktion aus (legt z. B. den Termin im Kalender an), ' +
            '„Verwerfen“ entfernt ihn ohne etwas zu tun.'
          }
        />

        <ErrorMessage message={listError} />
        <div className="mb-3">
          <ErrorMessage message={actionError} />
        </div>

        {loading ? (
          <p className="text-sm text-zinc-500">Lade...</p>
        ) : suggestions.length === 0 ? (
          <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-700">
            <p>Aktuell keine offenen Vorschläge.</p>
            <p className="mt-2">
              Das ist normal, solange noch keine passende Benachrichtigung erkannt wurde. Voraussetzungen:
            </p>
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              <li>Die Android-App ist installiert und eingeloggt</li>
              <li>&bdquo;Notification access&ldquo; wurde der App erlaubt (Einstellungen im Handy)</li>
              <li>
                Es kam eine Nachricht rein, in der OwnAI einen Termin oder eine sinnvolle Antwort
                erkennt (z. B. &bdquo;Bist du heute um 19 Uhr da?&ldquo;) — nicht jede Nachricht löst
                einen Vorschlag aus
              </li>
            </ul>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {suggestions.map((s) => (
              <li key={s.id} className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="mb-1 inline-block rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                      {s.kind === "calendar_event" ? "Kalendertermin" : "Antwortvorschlag"}
                    </span>
                    <p className="text-sm text-zinc-900 dark:text-zinc-100">{s.summary}</p>
                    <p className="mt-1 text-xs text-zinc-400">{formatTime(s.created_at)}</p>
                    <SuggestionDetails suggestion={s} />
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => handleApply(s.id)}
                      disabled={pendingId === s.id}
                      className="rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
                    >
                      Übernehmen
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDismiss(s.id)}
                      disabled={pendingId === s.id}
                      className="rounded-md border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    >
                      Verwerfen
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
