"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Modal } from "@/components/Modal";
import { ApiError } from "@/lib/api-client";
import * as agentsApi from "@/lib/api/permanentAgents";
import type { AgentLogEntry, AgentPreset, PermanentAgent } from "@/lib/types";

function formatTime(iso: string | null): string {
  if (!iso) return "Noch nie gelaufen";
  try {
    return new Date(iso).toLocaleString("de-DE");
  } catch {
    return iso;
  }
}

function NewAgentForm({ presets, onCreated }: { presets: AgentPreset[]; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [preset, setPreset] = useState(presets[0]?.key ?? "");
  const [rolePrompt, setRolePrompt] = useState("");
  const [intervalMinutes, setIntervalMinutes] = useState("60");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await agentsApi.createAgent({
        name: name.trim(),
        preset,
        role_prompt: rolePrompt.trim(),
        interval_minutes: Number(intervalMinutes),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Anlegen fehlgeschlagen.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <input
        type="text"
        required
        placeholder="Name, z.B. 'Krypto-Beobachter'"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
      />
      <select
        value={preset}
        onChange={(e) => setPreset(e.target.value)}
        className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
      >
        {presets.map((p) => (
          <option key={p.key} value={p.key}>
            {p.name}
          </option>
        ))}
      </select>
      <p className="-mt-1 text-xs text-zinc-500">
        {presets.find((p) => p.key === preset)?.description}
      </p>
      <textarea
        required
        placeholder="Was soll er genau beobachten/tun? z.B. 'Beobachte den Bitcoin-Kurs, melde nur bei Bewegungen über 5%.'"
        value={rolePrompt}
        onChange={(e) => setRolePrompt(e.target.value)}
        rows={3}
        className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
      />
      <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
        Intervall:
        <select
          value={intervalMinutes}
          onChange={(e) => setIntervalMinutes(e.target.value)}
          className="rounded-xl border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        >
          <option value="15">15 Minuten</option>
          <option value="30">30 Minuten</option>
          <option value="60">1 Stunde</option>
          <option value="180">3 Stunden</option>
          <option value="360">6 Stunden</option>
          <option value="1440">1 Tag</option>
        </select>
      </label>
      <ErrorMessage message={error} />
      <button
        type="submit"
        disabled={creating || !name.trim() || !rolePrompt.trim()}
        className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {creating ? "Lege an..." : "Agent anlegen"}
      </button>
    </form>
  );
}

function AgentLog({ entries }: { entries: AgentLogEntry[] }) {
  if (entries.length === 0) {
    return <p className="px-3 py-2 text-xs text-zinc-500">Noch keine Läufe.</p>;
  }
  return (
    <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
      {entries.map((e) => (
        <li key={e.id} className="px-3 py-2 text-sm">
          <div className="mb-0.5 flex items-center gap-2 text-xs text-zinc-400">
            <span>{formatTime(e.created_at)}</span>
            {e.notable && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700 dark:bg-amber-950 dark:text-amber-400">
                wichtig
              </span>
            )}
          </div>
          <p className="whitespace-pre-line text-zinc-700 dark:text-zinc-300">{e.content}</p>
        </li>
      ))}
    </ul>
  );
}

export function PermanentAgentsTab() {
  const [presets, setPresets] = useState<AgentPreset[]>([]);
  const [agents, setAgents] = useState<PermanentAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewAgent, setShowNewAgent] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [logEntries, setLogEntries] = useState<AgentLogEntry[]>([]);
  const [logLoading, setLogLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([agentsApi.listPresets(), agentsApi.listAgents()])
      .then(([presetList, agentList]) => {
        setPresets(presetList);
        setAgents(agentList);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void (async () => {
      load();
    })();
  }, [load]);

  function presetLabel(key: string): string {
    return presets.find((p) => p.key === key)?.name ?? key;
  }

  async function handleToggleActive(agent: PermanentAgent) {
    try {
      const updated = await agentsApi.updateAgent(agent.id, { active: !agent.active });
      setAgents((prev) => prev.map((a) => (a.id === agent.id ? updated : a)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ändern fehlgeschlagen.");
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Diesen Agenten wirklich löschen (inkl. seines gesamten Logs)?")) return;
    try {
      await agentsApi.deleteAgent(id);
      setAgents((prev) => prev.filter((a) => a.id !== id));
      if (expandedId === id) setExpandedId(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  async function handleToggleLog(id: string) {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    setLogLoading(true);
    try {
      const entries = await agentsApi.listLog(id);
      setLogEntries(entries);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Log konnte nicht geladen werden.");
    } finally {
      setLogLoading(false);
    }
  }

  return (
    <div>
      <p className="mb-4 text-sm text-zinc-500">
        Permanente Agenten laufen eigenständig weiter, auch wenn du gerade nicht mit ihnen sprichst —
        sie wachen in festen Abständen auf, arbeiten mit einem festen (nur lesenden) Werkzeug-Preset
        und melden Wichtiges per Push. Anlegen geht auch per Zuruf im Chat/Voice (&bdquo;leg mir einen
        Agenten an, der ...&ldquo;).
      </p>

      <ErrorMessage message={error} />

      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Deine Agenten</h3>
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
        <p className="text-sm text-zinc-500">Noch keine permanenten Agenten.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-2xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {agents.map((agent) => (
            <li key={agent.id}>
              <div className="animate-fade-in-up flex items-center justify-between gap-3 px-3 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60">
                <div className={agent.active ? "" : "opacity-50"}>
                  <p className="text-zinc-900 dark:text-zinc-100">{agent.name}</p>
                  <p className="text-xs text-zinc-400">
                    {presetLabel(agent.preset)} · alle {agent.interval_minutes} Min · {formatTime(agent.last_run_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleToggleLog(agent.id)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
                  >
                    {expandedId === agent.id ? "Log verbergen" : "Log anzeigen"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleToggleActive(agent)}
                    className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                  >
                    {agent.active ? "Pausieren" : "Aktivieren"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(agent.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Löschen
                  </button>
                </div>
              </div>
              {expandedId === agent.id && (
                <div className="border-t border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
                  {logLoading ? (
                    <p className="px-3 py-2 text-xs text-zinc-500">Lade Log...</p>
                  ) : (
                    <AgentLog entries={logEntries} />
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {showNewAgent ? (
        <Modal title="Neuer permanenter Agent" onClose={() => setShowNewAgent(false)}>
          <NewAgentForm
            presets={presets}
            onCreated={() => {
              load();
              setShowNewAgent(false);
            }}
          />
        </Modal>
      ) : null}
    </div>
  );
}
