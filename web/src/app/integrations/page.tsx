"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { SetupHelperChat } from "@/components/SetupHelperChat";
import { ApiError } from "@/lib/api-client";
import * as calendarApi from "@/lib/api/calendar";
import * as homeAssistantApi from "@/lib/api/homeAssistant";

type ConnectionStatus = "checking" | "connected" | "not_connected" | "error";

function StatusBadge({ status }: { status: ConnectionStatus }) {
  if (status === "checking") return <span className="text-xs text-zinc-400">Prüfe...</span>;
  if (status === "connected") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
        <span className="h-1.5 w-1.5 rounded-full bg-green-500" /> Verbunden
      </span>
    );
  }
  if (status === "not_connected") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-zinc-500">
        <span className="h-1.5 w-1.5 rounded-full bg-zinc-400" /> Nicht verbunden
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600 dark:text-red-400">
      <span className="h-1.5 w-1.5 rounded-full bg-red-500" /> Fehler
    </span>
  );
}

function CaldavCard() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  useEffect(() => {
    const now = new Date();
    calendarApi
      .listEvents(now.toISOString(), now.toISOString())
      .then(() => setStatus("connected"))
      .catch((err) => {
        if (err instanceof ApiError && err.code === "calendar_not_connected") {
          setStatus("not_connected");
        } else {
          setStatus("error");
        }
      });
  }, []);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setConnectError(null);
    setConnecting(true);
    try {
      await calendarApi.connectCaldav({ url, username, password });
      setStatus("connected");
      setPassword("");
    } catch (err) {
      setConnectError(err instanceof ApiError ? err.message : "Verbindung fehlgeschlagen.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Kalender (CalDAV)</h2>
        <StatusBadge status={status} />
      </div>
      <p className="mb-3 text-xs text-zinc-500">
        Verbinde deinen CalDAV-Kalender, damit OwnAI Termine lesen und anlegen kann — über Chat, Voice
        oder auf der Kalender-Seite.
      </p>
      <form onSubmit={handleConnect} className="flex flex-col gap-3">
        <input
          type="url"
          required
          placeholder="CalDAV URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="text"
          required
          placeholder="Benutzername"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="password"
          required
          placeholder="Passwort"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <ErrorMessage message={connectError} />
        <button
          type="submit"
          disabled={connecting}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {connecting ? "Verbinde..." : status === "connected" ? "Neu verbinden" : "Verbinden"}
        </button>
      </form>
    </div>
  );
}

function HomeAssistantCard() {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [entityCount, setEntityCount] = useState<number | null>(null);

  const checkStatus = useCallback(() => {
    homeAssistantApi
      .listEntities()
      .then((entities) => {
        setStatus("connected");
        setEntityCount(entities.length);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.code === "home_assistant_not_connected") {
          setStatus("not_connected");
        } else {
          setStatus("error");
        }
      });
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setConnectError(null);
    setConnecting(true);
    try {
      await homeAssistantApi.connectHomeAssistant({ url, token });
      setToken("");
      checkStatus();
    } catch (err) {
      setConnectError(err instanceof ApiError ? err.message : "Verbindung fehlgeschlagen.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Home Assistant</h2>
        <StatusBadge status={status} />
      </div>
      <p className="mb-3 text-xs text-zinc-500">
        Verbinde deine eigene Home-Assistant-Instanz, damit OwnAI Geräte steuern kann (Licht, Steckdosen,
        Heizung, ...) — über Chat oder Voice.
        {status === "connected" && entityCount !== null ? ` ${entityCount} Geräte gefunden.` : ""}
      </p>
      <form onSubmit={handleConnect} className="flex flex-col gap-3">
        <input
          type="url"
          required
          placeholder="Home Assistant URL (z.B. http://homeassistant.local:8123)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="password"
          required
          placeholder="Long-Lived Access Token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <ErrorMessage message={connectError} />
        <button
          type="submit"
          disabled={connecting}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {connecting ? "Verbinde..." : status === "connected" ? "Neu verbinden" : "Verbinden"}
        </button>
      </form>
    </div>
  );
}

export default function IntegrationsPage() {
  return (
    <AppShell>
      <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-4 lg:flex-row lg:items-start lg:overflow-hidden">
        <section className="flex w-full flex-col gap-4 lg:w-96 lg:overflow-y-auto">
          <CaldavCard />
          <HomeAssistantCard />
        </section>
        <section className="min-h-[28rem] flex-1 lg:h-full">
          <SetupHelperChat />
        </section>
      </div>
    </AppShell>
  );
}
