"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as rssApi from "@/lib/api/rss";
import type { RssFeed, RssItem } from "@/lib/types";

function formatDate(value: string | null): string {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch {
    return value;
  }
}

export function RssTab() {
  const [feeds, setFeeds] = useState<RssFeed[]>([]);
  const [loadingFeeds, setLoadingFeeds] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [url, setUrl] = useState("");
  const [adding, setAdding] = useState(false);

  const [items, setItems] = useState<RssItem[] | null>(null);
  const [loadingItems, setLoadingItems] = useState(false);

  const loadFeeds = useCallback(() => {
    setLoadingFeeds(true);
    rssApi
      .listFeeds()
      .then(setFeeds)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoadingFeeds(false));
  }, []);

  useEffect(() => {
    void (async () => {
      loadFeeds();
    })();
  }, [loadFeeds]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await rssApi.createFeed(url.trim());
      setUrl("");
      loadFeeds();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await rssApi.deleteFeed(id);
      setFeeds((prev) => prev.filter((f) => f.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  async function handleShowLatest(feedId?: string) {
    setLoadingItems(true);
    setError(null);
    setItems(null);
    try {
      const result = await rssApi.listItems(feedId);
      setItems(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Neuigkeiten konnten nicht geladen werden.");
    } finally {
      setLoadingItems(false);
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        RSS/Atom-Feeds abonnieren, damit sich der Assistent Neuigkeiten daraus zusammenfassen kann — im
        Chat/Voice frag einfach &bdquo;was gibt&apos;s Neues bei [Feed]?&ldquo; oder klick unten auf
        &bdquo;Neuigkeiten anzeigen&ldquo;.
      </p>

      <form onSubmit={handleAdd} className="mb-4 flex gap-2">
        <input
          type="url"
          placeholder="Feed-URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={adding || !url.trim()}
          className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {adding ? "Füge hinzu..." : "Abonnieren"}
        </button>
      </form>

      <ErrorMessage message={error} />

      {loadingFeeds ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : feeds.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch keine Feeds abonniert.</p>
      ) : (
        <>
          <ul className="mb-3 divide-y divide-zinc-200 rounded-2xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
            {feeds.map((f) => (
              <li key={f.id} className="animate-fade-in-up flex items-center justify-between gap-3 px-3 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60">
                <div>
                  <p className="text-zinc-900 dark:text-zinc-100">{f.name || f.url}</p>
                  <p className="text-xs text-zinc-400">{f.url}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleShowLatest(f.id)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
                  >
                    Neuigkeiten
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(f.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Löschen
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => handleShowLatest()}
            className="mb-3 text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
          >
            Neuigkeiten aus allen Feeds anzeigen
          </button>
        </>
      )}

      {loadingItems && <p className="text-sm text-zinc-500">Lade Neuigkeiten...</p>}

      {items && (
        <ul className="flex flex-col gap-2">
          {items.length === 0 ? (
            <p className="text-sm text-zinc-500">Keine Einträge gefunden.</p>
          ) : (
            items.map((item, i) => (
              <li key={`${item.link}-${i}`} className="rounded-2xl border border-zinc-200 p-3 text-sm dark:border-zinc-800">
                <p className="text-xs text-zinc-400">
                  {item.feed_name}
                  {item.published ? ` · ${formatDate(item.published)}` : ""}
                </p>
                <a
                  href={item.link}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-zinc-900 hover:underline dark:text-zinc-100"
                >
                  {item.title}
                </a>
                {item.summary && <p className="mt-1 text-xs text-zinc-500">{item.summary}</p>}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
