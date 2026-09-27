"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Modal } from "@/components/Modal";
import { SetupHelperChat } from "@/components/SetupHelperChat";
import { ApiError } from "@/lib/api-client";
import * as calendarApi from "@/lib/api/calendar";
import * as homeAssistantApi from "@/lib/api/homeAssistant";

type ConnectionStatus = "checking" | "connected" | "not_connected" | "error";
type IntegrationKey = "caldav" | "home-assistant";

function StatusDot({ status }: { status: ConnectionStatus }) {
  const color =
    status === "connected"
      ? "bg-green-500"
      : status === "error"
        ? "bg-red-500"
        : status === "checking"
          ? "bg-zinc-300 dark:bg-zinc-600"
          : "bg-zinc-400";
  return <span className={`h-2 w-2 shrink-0 rounded-full ${color}`} />;
}

function statusLabel(status: ConnectionStatus): string {
  if (status === "checking") return "Prüfe...";
  if (status === "connected") return "Verbunden";
  if (status === "not_connected") return "Nicht verbunden";
  return "Fehler";
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <rect x="3" y="5" width="18" height="16" rx="2" stroke="currentColor" strokeWidth={2} />
      <path d="M3 9h18M8 3v4M16 3v4" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      <path
        d="M4 11l8-7 8 7M6 9.5V20a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1V9.5"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** A clickable tile in the integrations grid — icon, name, status, opens its config popup on click. */
function IntegrationTile({
  icon,
  name,
  description,
  status,
  onClick,
}: {
  icon: ReactNode;
  name: string;
  description: string;
  status: ConnectionStatus;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col items-start gap-2 rounded-lg border border-zinc-200 p-4 text-left transition-colors hover:border-zinc-300 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:border-zinc-700 dark:hover:bg-zinc-900"
    >
      <div className="flex w-full items-center justify-between">
        <span className="text-zinc-700 dark:text-zinc-300">{icon}</span>
        <span className="flex items-center gap-1.5 text-xs text-zinc-500">
          <StatusDot status={status} />
          {statusLabel(status)}
        </span>
      </div>
      <div>
        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{name}</p>
        <p className="mt-0.5 text-xs text-zinc-500">{description}</p>
      </div>
    </button>
  );
}

function CaldavForm({ onConnected }: { onConnected: () => void }) {
  const [url, setUrl] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setConnectError(null);
    setConnecting(true);
    try {
      await calendarApi.connectCaldav({ url, username, password });
      onConnected();
    } catch (err) {
      setConnectError(err instanceof ApiError ? err.message : "Verbindung fehlgeschlagen.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <form onSubmit={handleConnect} className="flex flex-col gap-3">
      <p className="text-xs text-zinc-500">
        Verbinde deinen CalDAV-Kalender, damit OwnAI Termine lesen und anlegen kann — über Chat, Voice
        oder auf der Kalender-Seite.
      </p>
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
        {connecting ? "Verbinde..." : "Verbinden"}
      </button>
    </form>
  );
}

function HomeAssistantForm({ onConnected }: { onConnected: () => void }) {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setConnectError(null);
    setConnecting(true);
    try {
      await homeAssistantApi.connectHomeAssistant({ url, token });
      onConnected();
    } catch (err) {
      setConnectError(err instanceof ApiError ? err.message : "Verbindung fehlgeschlagen.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <form onSubmit={handleConnect} className="flex flex-col gap-3">
      <p className="text-xs text-zinc-500">
        Verbinde deine eigene Home-Assistant-Instanz, damit OwnAI Geräte steuern kann (Licht,
        Steckdosen, Heizung, ...) — über Chat oder Voice. Jeder Nutzer verbindet seine eigene Instanz.
      </p>
      <input
        type="url"
        required
        placeholder="URL (z.B. http://homeassistant.local:8123)"
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
        {connecting ? "Verbinde..." : "Verbinden"}
      </button>
    </form>
  );
}

function ChatFab({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={open ? "Hilfe-Chat schließen" : "Hilfe-Chat öffnen"}
      className="fixed right-5 bottom-5 z-10 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500 text-white shadow-lg transition-transform hover:scale-105"
    >
      {open ? (
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
          <path
            d="M4 5h16v11H8l-4 4V5Z"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  );
}

export function IntegrationsTab() {
  const [caldavStatus, setCaldavStatus] = useState<ConnectionStatus>("checking");
  const [haStatus, setHaStatus] = useState<ConnectionStatus>("checking");
  const [openModal, setOpenModal] = useState<IntegrationKey | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);

  const checkCaldav = useCallback(() => {
    setCaldavStatus("checking");
    const now = new Date();
    calendarApi
      .listEvents(now.toISOString(), now.toISOString())
      .then(() => setCaldavStatus("connected"))
      .catch((err) => {
        setCaldavStatus(err instanceof ApiError && err.code === "calendar_not_connected" ? "not_connected" : "error");
      });
  }, []);

  const checkHomeAssistant = useCallback(() => {
    setHaStatus("checking");
    homeAssistantApi
      .listEntities()
      .then(() => setHaStatus("connected"))
      .catch((err) => {
        setHaStatus(
          err instanceof ApiError && err.code === "home_assistant_not_connected" ? "not_connected" : "error",
        );
      });
  }, []);

  useEffect(() => {
    void (async () => {
      checkCaldav();
      checkHomeAssistant();
    })();
  }, [checkCaldav, checkHomeAssistant]);

  return (
    <div>
      <p className="mb-4 text-sm text-zinc-500">
        Verbinde deine eigenen Dienste — auf eine Karte tippen, um sie einzurichten.
      </p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <IntegrationTile
          icon={<CalendarIcon />}
          name="Kalender"
          description="CalDAV"
          status={caldavStatus}
          onClick={() => setOpenModal("caldav")}
        />
        <IntegrationTile
          icon={<HomeIcon />}
          name="Home Assistant"
          description="Smart Home"
          status={haStatus}
          onClick={() => setOpenModal("home-assistant")}
        />
      </div>

      {openModal === "caldav" ? (
        <Modal title="Kalender (CalDAV)" onClose={() => setOpenModal(null)}>
          <CaldavForm
            onConnected={() => {
              checkCaldav();
              setOpenModal(null);
            }}
          />
        </Modal>
      ) : null}

      {openModal === "home-assistant" ? (
        <Modal title="Home Assistant" onClose={() => setOpenModal(null)}>
          <HomeAssistantForm
            onConnected={() => {
              checkHomeAssistant();
              setOpenModal(null);
            }}
          />
        </Modal>
      ) : null}

      <ChatFab open={helpOpen} onToggle={() => setHelpOpen((v) => !v)} />
      {helpOpen ? (
        <div className="fixed right-5 bottom-20 z-10 h-[28rem] w-[22rem] max-w-[calc(100vw-2.5rem)]">
          <SetupHelperChat />
        </div>
      ) : null}
    </div>
  );
}
