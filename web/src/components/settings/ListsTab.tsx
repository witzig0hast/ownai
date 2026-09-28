"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as listsApi from "@/lib/api/lists";
import type { ListKind, TodoList } from "@/lib/types";

function ListCard({ list, onChange, onError, onDeleteList }: {
  list: TodoList;
  onChange: (updated: TodoList) => void;
  onError: (message: string) => void;
  onDeleteList: (id: string) => void;
}) {
  const [newItem, setNewItem] = useState("");
  const [adding, setAdding] = useState(false);

  async function handleAddItem(e: FormEvent) {
    e.preventDefault();
    if (!newItem.trim()) return;
    setAdding(true);
    try {
      const updated = await listsApi.addItem(list.id, newItem.trim());
      onChange(updated);
      setNewItem("");
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleToggle(itemId: string, done: boolean) {
    try {
      const updated = await listsApi.updateItem(list.id, itemId, { done: !done });
      onChange(updated);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Ändern fehlgeschlagen.");
    }
  }

  async function handleDeleteItem(itemId: string) {
    try {
      const updated = await listsApi.deleteItem(list.id, itemId);
      onChange(updated);
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{list.kind === "shopping" ? "🛒" : "✅"}</span>
          <span className="font-medium text-zinc-900 dark:text-zinc-100">{list.name}</span>
        </div>
        <button
          type="button"
          onClick={() => onDeleteList(list.id)}
          className="text-xs text-red-500 hover:text-red-700"
        >
          Liste löschen
        </button>
      </div>

      {list.items.length === 0 ? (
        <p className="mb-2 text-xs text-zinc-400">Noch keine Einträge.</p>
      ) : (
        <ul className="mb-2 flex flex-col gap-1">
          {list.items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={item.done}
                onChange={() => handleToggle(item.id, item.done)}
                className="h-4 w-4"
              />
              <span className={`flex-1 ${item.done ? "text-zinc-400 line-through" : "text-zinc-900 dark:text-zinc-100"}`}>
                {item.content}
              </span>
              <button
                type="button"
                onClick={() => handleDeleteItem(item.id)}
                className="text-xs text-red-500 hover:text-red-700"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleAddItem} className="flex gap-2">
        <input
          type="text"
          placeholder="Neuer Eintrag..."
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={adding || !newItem.trim()}
          className="rounded-md bg-zinc-900 px-2 py-1 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          +
        </button>
      </form>
    </div>
  );
}

export function ListsTab() {
  const [lists, setLists] = useState<TodoList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [kind, setKind] = useState<ListKind>("shopping");
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    listsApi
      .listLists()
      .then(setLists)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void (async () => {
      load();
    })();
  }, [load]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const created = await listsApi.createList(name.trim(), kind);
      setLists((prev) => [...prev, created]);
      setName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erstellen fehlgeschlagen.");
    } finally {
      setCreating(false);
    }
  }

  function handleListChange(updated: TodoList) {
    setLists((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
  }

  async function handleDeleteList(id: string) {
    try {
      await listsApi.deleteList(id);
      setLists((prev) => prev.filter((l) => l.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Todo- und Einkaufslisten, die du auch im Chat oder per Sprache pflegen kannst (&bdquo;setz Milch auf
        die Einkaufsliste&ldquo;, &bdquo;hak Brot ab&ldquo;).
      </p>

      <form onSubmit={handleCreate} className="mb-4 flex gap-2 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
        <input
          type="text"
          placeholder="Name der neuen Liste"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as ListKind)}
          className="rounded-md border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        >
          <option value="shopping">Einkaufsliste</option>
          <option value="todo">Todo</option>
        </select>
        <button
          type="submit"
          disabled={creating || !name.trim()}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Anlegen
        </button>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : lists.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch keine Listen.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {lists.map((list) => (
            <ListCard
              key={list.id}
              list={list}
              onChange={handleListChange}
              onError={setError}
              onDeleteList={handleDeleteList}
            />
          ))}
        </div>
      )}
    </div>
  );
}
