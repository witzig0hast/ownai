"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Modal } from "@/components/Modal";
import { ApiError } from "@/lib/api-client";
import * as agentBusApi from "@/lib/api/agentBus";
import type { AgentIdentity, AgentMessage } from "@/lib/types";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusColor(status: AgentMessage["status"]): string {
  if (status === "completed" || status === "sent") return "text-green-600 dark:text-green-400";
  if (status === "failed") return "text-red-600 dark:text-red-400";
  return "text-amber-600 dark:text-amber-400";
}

function NewAgentForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const created = await agentBusApi.registerAgent(name.trim(), description.trim() || null);
      setCreatedKey(created.api_key);
      setName("");
      setDescription("");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anlegen fehlgeschlagen.");
    } finally {
      setCreating(false);
    }
  }

  if (createdKey) {
    return (
      <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950">
        <p className="mb-2 font-medium text-amber-900 dark:text-amber-200">
          Agent-Schlüssel (nur jetzt sichtbar, gut aufbewahren):
        </p>
        <code className="block rounded bg-white px-2 py-1.5 text-xs break-all text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100">
          {createdKey}
        </code>
        <button
          type="button"
          onClick={() => setCreatedKey(null)}
          className="mt-3 rounded-xl bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Verstanden
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <input
        type="text"
        required
        placeholder="Name, z.B. shop-backend"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
      />
      <input
        type="text"
        placeholder="Beschreibung (optional)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
      />
      <ErrorMessage message={error} />
      <button
        type="submit"
        disabled={creating}
        className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {creating ? "Registriere..." : "Agent registrieren"}
      </button>
    </form>
  );
}

export function AgentBusTab() {
  const [agents, setAgents] = useState<AgentIdentity[]>([]);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [showNewAgent, setShowNewAgent] = useState(false);

  const loadAll = useCallback(() => {
    setLoading(true);
    setListError(null);
    Promise.all([agentBusApi.listAgents(), agentBusApi.listMessages()])
      .then(([agentsList, messagesList]) => {
        setAgents(agentsList);
        setMessages(messagesList);
      })
      .catch((err) => setListError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void (async () => {
      loadAll();
    })();
  }, [loadAll]);

  async function handleDelete(agent: AgentIdentity) {
    if (!window.confirm(`Agent "${agent.name}" wirklich entfernen?`)) return;
    try {
      await agentBusApi.deleteAgent(agent.id);
      loadAll();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div>
      <p className="mb-4 text-sm text-zinc-500">
        Registriere eigene andere Projekte/Webseiten als Agents, damit sie mit OwnAI Nachrichten und
        Aufgaben austauschen können — über einen einzigen, geloggten Bus. Eine Nachricht an{" "}
        <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">ownai</code> erreicht dich direkt (inkl.
        Push-Benachrichtigung), ohne dass du vorher fragen musst.
      </p>

      <ErrorMessage message={listError} />

      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Registrierte Agents</h3>
          <button
            type="button"
            onClick={() => setShowNewAgent(true)}
            className="rounded-xl bg-zinc-900 px-2 py-1 text-xs font-medium text-white shadow-sm transition-all hover:scale-105 hover:bg-zinc-700 active:scale-95 dark:bg-zinc-100 dark:text-zinc-900"
          >
            + Neuer Agent
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-zinc-500">Lade...</p>
        ) : agents.length === 0 ? (
          <p className="text-sm text-zinc-500">Noch keine Agents registriert.</p>
        ) : (
          <ul className="divide-y divide-zinc-200 rounded-2xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
            {agents.map((agent, i) => (
              <li
                key={agent.id}
                className="animate-fade-in-up flex items-center justify-between px-3 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
                style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
              >
                <div>
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">{agent.name}</span>
                  {agent.description ? (
                    <span className="ml-2 text-xs text-zinc-500">{agent.description}</span>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(agent)}
                  className="rounded-full px-2 py-1 text-xs text-red-500 transition-all hover:scale-105 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/40"
                >
                  Entfernen
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">Nachrichten-Log</h3>
        {loading ? (
          <p className="text-sm text-zinc-500">Lade...</p>
        ) : messages.length === 0 ? (
          <p className="text-sm text-zinc-500">Noch keine Nachrichten.</p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-zinc-200 dark:border-zinc-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
                <tr>
                  <th className="px-3 py-2 font-medium">Von</th>
                  <th className="px-3 py-2 font-medium">An</th>
                  <th className="px-3 py-2 font-medium">Art</th>
                  <th className="px-3 py-2 font-medium">Inhalt</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Zeit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {messages.map((m, i) => (
                  <tr
                    key={m.id}
                    className="animate-fade-in-up transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60"
                    style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}
                  >
                    <td className="px-3 py-2">{m.from_label}</td>
                    <td className="px-3 py-2">{m.to_label}</td>
                    <td className="px-3 py-2">{m.kind === "task" ? m.task_type || "task" : "text"}</td>
                    <td className="max-w-xs truncate px-3 py-2 text-zinc-600 dark:text-zinc-400">
                      {m.content || "—"}
                    </td>
                    <td className={`px-3 py-2 font-medium ${statusColor(m.status)}`}>{m.status}</td>
                    <td className="px-3 py-2 text-xs text-zinc-400">{formatTime(m.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showNewAgent ? (
        <Modal title="Neuer Agent" onClose={() => setShowNewAgent(false)}>
          <NewAgentForm onCreated={loadAll} />
        </Modal>
      ) : null}
    </div>
  );
}
