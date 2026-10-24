"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import { searchAll, type SearchResult, type SearchResultType } from "@/lib/api/search";
import { formatDate } from "@/lib/format";

const GROUP_LABEL: Record<SearchResultType, string> = {
  conversation: "Unterhaltungen",
  memory: "Gedächtnis",
  contact: "Kontakte",
  list_item: "Listen",
  reminder: "Erinnerungen",
  expense: "Ausgaben",
};
const GROUP_ORDER: SearchResultType[] = ["conversation", "memory", "contact", "list_item", "reminder", "expense"];

function Highlight({ text, query }: { text: string; query: string }) {
  const i = text.toLowerCase().indexOf(query.toLowerCase());
  if (i < 0 || !query) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark className="rounded bg-indigo-100 px-0.5 text-inherit dark:bg-indigo-900/60">{text.slice(i, i + query.length)}</mark>
      {text.slice(i + query.length)}
    </>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) return;
    const controller = new AbortController();
    // Debounced, and each new keystroke aborts the previous request so results never arrive out
    // of order.
    const timer = setTimeout(() => {
      setLoading(true);
      searchAll(q, controller.signal)
        .then((r) => {
          setResults(r);
          setError(null);
        })
        .catch((err) => {
          if (controller.signal.aborted) return;
          setError(err instanceof ApiError ? err.message : "Suche fehlgeschlagen.");
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  const q = query.trim();
  const visible = q.length >= 2 ? results : null;
  const grouped = GROUP_ORDER.map((type) => ({ type, items: (visible ?? []).filter((r) => r.type === type) })).filter(
    (g) => g.items.length > 0,
  );

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto w-full max-w-2xl">
          <h1 className="mb-4 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">Suchen</h1>
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Unterhaltungen, Gedächtnis, Kontakte, Listen, Ausgaben..."
            aria-label="Suchbegriff"
            className="w-full rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-base shadow-sm focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
          />
          <div className="mt-4">
            <ErrorMessage message={error} />
            {q.length < 2 ? (
              <p className="text-sm text-zinc-500">Mindestens zwei Zeichen eingeben.</p>
            ) : loading && !visible ? (
              <p className="text-sm text-zinc-500">Suche...</p>
            ) : visible && grouped.length === 0 ? (
              <p className="text-sm text-zinc-500">Nichts gefunden für „{q}“.</p>
            ) : null}

            <div className={`flex flex-col gap-5 transition-opacity ${loading ? "opacity-60" : ""}`}>
              {grouped.map((group) => (
                <section key={group.type}>
                  <h2 className="mb-1.5 text-xs font-semibold tracking-wide text-zinc-400 uppercase">
                    {GROUP_LABEL[group.type]}
                  </h2>
                  <ul className="flex flex-col divide-y divide-zinc-100 rounded-2xl border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-950">
                    {group.items.map((r) => (
                      <li key={`${r.type}-${r.id}`}>
                        <Link href={r.href} className="flex items-start justify-between gap-3 px-4 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-900">
                          <span className="min-w-0">
                            <span className="block truncate text-sm text-zinc-900 dark:text-zinc-100">
                              <Highlight text={r.title} query={q} />
                            </span>
                            {r.snippet ? (
                              <span className="mt-0.5 block text-xs text-zinc-500">
                                <Highlight text={r.snippet} query={q} />
                              </span>
                            ) : null}
                          </span>
                          {r.date ? <span className="shrink-0 text-xs text-zinc-400">{formatDate(r.date)}</span> : null}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
