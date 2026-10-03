"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Modal } from "@/components/Modal";
import * as pendingActionsApi from "@/lib/api/pendingActions";
import type { PendingAction } from "@/lib/types";

const POLL_INTERVAL_MS = 30000;

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

/**
 * Autonome Agenten (aktuell: eingehende E-Mails, siehe EmailTab) schlagen konsequente Aktionen
 * (E-Mail senden, etwas löschen, ein Gerät steuern, ...) nur vor, statt sie direkt auszuführen -
 * der Nutzer hat das explizit so gewollt, nachdem er zunächst volle Autonomie hatte. Diese
 * Komponente pollt die offenen Vorschläge und öffnet automatisch ein Popup, sobald mindestens
 * einer neu ist (nicht bei jedem Poll erneut, falls der Nutzer das Popup schon gesehen/
 * geschlossen hat) - ein manueller Klick auf das Badge öffnet es jederzeit wieder.
 */
export function PendingActionsGate() {
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [open, setOpen] = useState(false);
  const [decidingId, setDecidingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seenIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      pendingActionsApi
        .listPendingActions()
        .then((list) => {
          if (cancelled) return;
          setActions(list);
          const hasUnseen = list.some((a) => !seenIdsRef.current.has(a.id));
          for (const a of list) seenIdsRef.current.add(a.id);
          if (hasUnseen && list.length > 0) setOpen(true);
        })
        .catch(() => {
          // a failed poll just means we try again next interval
        });
    };
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const decide = useCallback(async (id: string, decision: "approve" | "decline") => {
    setDecidingId(id);
    setError(null);
    try {
      const fn = decision === "approve" ? pendingActionsApi.approvePendingAction : pendingActionsApi.declinePendingAction;
      await fn(id);
      setActions((prev) => prev.filter((a) => a.id !== id));
    } catch {
      setError("Aktion konnte nicht verarbeitet werden. Bitte erneut versuchen.");
    } finally {
      setDecidingId(null);
    }
  }, []);

  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex animate-pulse items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 transition-all hover:scale-105 active:scale-95 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300"
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
          <path d="M12 9v4M12 17h.01" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
          <path
            d="M10.29 3.86 1.82 18a1 1 0 0 0 .86 1.5h18.64a1 1 0 0 0 .86-1.5L13.71 3.86a1 1 0 0 0-1.72 0Z"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinejoin="round"
          />
        </svg>
        {actions.length} wartet{actions.length === 1 ? "" : "en"} auf dich
      </button>

      {open ? (
        <Modal title="Bestätigung ausstehend" onClose={() => setOpen(false)}>
          <p className="mb-3 text-sm text-zinc-500">
            Ein autonomer Agent möchte Folgendes tun — bestätige oder lehne jeden Vorschlag einzeln ab.
          </p>
          {error ? <p className="mb-3 text-sm text-red-500">{error}</p> : null}
          <ul className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {actions.map((action) => (
              <li
                key={action.id}
                className="rounded-2xl border border-zinc-200 p-3 text-sm dark:border-zinc-800"
              >
                <p className="mb-1 text-zinc-900 dark:text-zinc-100">{action.summary}</p>
                <p className="mb-2 text-xs text-zinc-400">{formatTime(action.created_at)}</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => decide(action.id, "approve")}
                    disabled={decidingId === action.id}
                    className="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm transition-all hover:scale-105 hover:bg-emerald-500 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
                  >
                    Bestätigen
                  </button>
                  <button
                    type="button"
                    onClick={() => decide(action.id, "decline")}
                    disabled={decidingId === action.id}
                    className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-all hover:scale-105 hover:bg-red-50 hover:text-red-700 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-red-950/40"
                  >
                    Ablehnen
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </Modal>
      ) : null}
    </div>
  );
}
