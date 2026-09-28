"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as emailApi from "@/lib/api/email";
import type { EmailStatus } from "@/lib/api/email";

export function EmailTab() {
  const [status, setStatus] = useState<EmailStatus | "checking" | "error">("checking");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("587");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fromAddress, setFromAddress] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const loadStatus = useCallback(() => {
    setStatus("checking");
    emailApi
      .getEmailStatus()
      .then(setStatus)
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    void (async () => {
      loadStatus();
    })();
  }, [loadStatus]);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setConnectError(null);
    setConnecting(true);
    try {
      await emailApi.connectEmail({
        smtp_host: host,
        smtp_port: Number(port) || 587,
        smtp_username: username,
        smtp_password: password,
        from_address: fromAddress,
        use_tls: useTls,
      });
      setPassword("");
      loadStatus();
    } catch (err) {
      setConnectError(err instanceof ApiError ? err.message : "Verbindung fehlgeschlagen.");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="max-w-md">
      <p className="mb-4 text-sm text-zinc-500">
        Verbinde dein eigenes SMTP-Konto, damit der Assistent E-Mails in deinem Namen verschicken kann.
        Ohne eigenes Konto nutzt er, falls vorhanden, die System-Standard-Adresse.
      </p>

      <div className="animate-fade-in-up mb-4 rounded-2xl border border-zinc-200 p-4 text-sm shadow-sm dark:border-zinc-800">
        {status === "checking" ? (
          <span className="text-zinc-500">Prüfe...</span>
        ) : status === "error" ? (
          <span className="text-red-500">Status konnte nicht geladen werden.</span>
        ) : status.has_custom_account ? (
          <span className="text-zinc-900 dark:text-zinc-100">
            Eigenes Konto verbunden — sendet als <strong>{status.effective_from_address}</strong>.
          </span>
        ) : status.effective_from_address ? (
          <span className="text-zinc-900 dark:text-zinc-100">
            Kein eigenes Konto — nutzt die System-Standard-Adresse{" "}
            <strong>{status.effective_from_address}</strong>.
          </span>
        ) : (
          <span className="text-zinc-500">
            Weder ein eigenes Konto noch eine System-Standard-Adresse konfiguriert — der Assistent kann
            aktuell keine E-Mails senden.
          </span>
        )}
      </div>

      <form onSubmit={handleConnect} className="flex flex-col gap-3">
        <input
          type="text"
          required
          placeholder="SMTP-Host, z.B. smtp.gmail.com"
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="number"
          required
          placeholder="Port"
          value={port}
          onChange={(e) => setPort(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="text"
          required
          placeholder="Benutzername"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="password"
          required
          placeholder="Passwort"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <input
          type="email"
          required
          placeholder="Absenderadresse"
          value={fromAddress}
          onChange={(e) => setFromAddress(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={useTls}
            onChange={(e) => setUseTls(e.target.checked)}
            className="h-5 w-5 cursor-pointer accent-indigo-500"
          />
          TLS verwenden (empfohlen)
        </label>
        <ErrorMessage message={connectError} />
        <button
          type="submit"
          disabled={connecting}
          className="rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {connecting ? "Verbinde..." : "Verbinden"}
        </button>
      </form>
    </div>
  );
}
