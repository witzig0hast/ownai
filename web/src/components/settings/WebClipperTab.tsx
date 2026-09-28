"use client";

import { useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as clipperApi from "@/lib/api/clipper";
import type { ClippedPage } from "@/lib/types";

export function WebClipperTab() {
  const [url, setUrl] = useState("");
  const [clipped, setClipped] = useState<ClippedPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClip(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await clipperApi.clipUrl(url.trim());
      setClipped(result);
    } catch (err) {
      setClipped(null);
      setError(err instanceof ApiError ? err.message : "Seite konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Web-Clipper: extrahiert den lesbaren Text einer Seite (ohne Navigation/Werbung). Frag den
        Assistenten im Chat/Voice, eine Seite zusammenzufassen oder als Datei zu speichern — hier
        siehst du nur die Vorschau.
      </p>

      <form onSubmit={handleClip} className="mb-4 flex gap-2">
        <input
          type="url"
          placeholder="URL, z.B. https://example.com/artikel"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {loading ? "Lade..." : "Abrufen"}
        </button>
      </form>

      <ErrorMessage message={error} />

      {clipped && (
        <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <p className="mb-1 text-lg font-medium text-zinc-900 dark:text-zinc-100">{clipped.title}</p>
          <a
            href={clipped.url}
            target="_blank"
            rel="noreferrer"
            className="mb-3 block text-xs text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {clipped.url}
          </a>
          <p className="max-h-96 overflow-y-auto whitespace-pre-line text-sm text-zinc-700 dark:text-zinc-300">
            {clipped.text}
          </p>
        </div>
      )}
    </div>
  );
}
