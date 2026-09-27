"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as memoryApi from "@/lib/api/memory";
import type { Memory } from "@/lib/types";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

export function MemoryTab() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newContent, setNewContent] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    memoryApi
      .listMemories()
      .then(setMemories)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void (async () => {
      load();
    })();
  }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newContent.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await memoryApi.createMemory(newContent.trim());
      setNewContent("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await memoryApi.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Fakten, die sich der Assistent über dich gemerkt hat (automatisch, während ihr chattet, oder
        manuell hier) — er zieht sie in jede Unterhaltung mit ein, ohne dass du sie wiederholen musst.
      </p>

      <form onSubmit={handleAdd} className="mb-4 flex gap-2">
        <input
          type="text"
          placeholder="Fakt hinzufügen, z.B. 'Mag keine Zwiebeln'"
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={adding || !newContent.trim()}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Hinzufügen
        </button>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : memories.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch nichts gemerkt.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {memories.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
              <div>
                <p className="text-zinc-900 dark:text-zinc-100">{m.content}</p>
                <p className="text-xs text-zinc-400">{formatTime(m.created_at)}</p>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(m.id)}
                className="shrink-0 text-xs text-red-500 hover:text-red-700"
              >
                Löschen
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
