"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as automationsApi from "@/lib/api/automations";
import type { Automation } from "@/lib/types";

export function AutomationsTab() {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [entityId, setEntityId] = useState("");
  const [triggerState, setTriggerState] = useState("");
  const [message, setMessage] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    automationsApi
      .listAutomations()
      .then(setAutomations)
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
    if (!entityId.trim() || !triggerState.trim() || !message.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await automationsApi.createAutomation({
        entity_id: entityId.trim(),
        trigger_state: triggerState.trim(),
        message: message.trim(),
      });
      setEntityId("");
      setTriggerState("");
      setMessage("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleToggleActive(automation: Automation) {
    try {
      const updated = await automationsApi.updateAutomation(automation.id, { active: !automation.active });
      setAutomations((prev) => prev.map((a) => (a.id === automation.id ? updated : a)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ändern fehlgeschlagen.");
    }
  }

  async function handleDelete(id: string) {
    try {
      await automationsApi.deleteAutomation(id);
      setAutomations((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Wirst du per Push benachrichtigt, sobald eine Home-Assistant-Entität einen bestimmten Zustand
        erreicht (z.B. Tür wird aufgeschlossen). Die entity_id findest du auf dem Integrations-Tab bzw.
        kann dir der Assistent im Chat nennen. Feuert nur bei Zustandswechsel, nicht wiederholt.
      </p>

      <form onSubmit={handleAdd} className="mb-4 flex flex-col gap-2 rounded-2xl border border-zinc-200 p-3 dark:border-zinc-800">
        <input
          type="text"
          placeholder="entity_id, z.B. 'lock.haustuer'"
          value={entityId}
          onChange={(e) => setEntityId(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="text"
          placeholder="Zustand, der auslöst, z.B. 'unlocked'"
          value={triggerState}
          onChange={(e) => setTriggerState(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="text"
          placeholder="Nachricht, z.B. 'Haustür ist auf'"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={adding || !entityId.trim() || !triggerState.trim() || !message.trim()}
          className="self-start rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Automatisierung hinzufügen
        </button>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : automations.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch keine Automatisierungen.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-2xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {automations.map((a) => (
            <li key={a.id} className="animate-fade-in-up flex items-center justify-between gap-3 px-3 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60">
              <div className={a.active ? "" : "opacity-50"}>
                <p className="text-zinc-900 dark:text-zinc-100">{a.message}</p>
                <p className="text-xs text-zinc-400">
                  {a.entity_id} → {a.trigger_state}
                  {a.last_seen_state != null && ` (aktuell: ${a.last_seen_state})`}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <button
                  type="button"
                  onClick={() => handleToggleActive(a)}
                  className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                >
                  {a.active ? "Pausieren" : "Aktivieren"}
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(a.id)}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  Löschen
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
