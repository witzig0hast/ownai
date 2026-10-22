"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import * as onboardingApi from "@/lib/api/onboarding";
import type { SetupStatus } from "@/lib/api/onboarding";

/**
 * "Einrichtung" checklist (GET /users/me/setup-status): what a new user still has to connect
 * before the assistant can actually do much. Hidden once everything is done or the user hid it
 * (stored server-side, so it stays hidden on every device; the help page can bring it back).
 *
 * `variant="voice"` starts collapsed as a one-line banner so it doesn't crowd the mic button;
 * `variant="settings"` starts expanded. `refreshKey` re-fetches when it changes - the settings
 * page passes the active tab, so finishing a step there ticks it off without a reload.
 */
export function SetupChecklist({ variant, refreshKey }: { variant: "voice" | "settings"; refreshKey?: string }) {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [expanded, setExpanded] = useState(variant === "settings");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    onboardingApi
      .getSetupStatus()
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  if (!status || status.dismissed || status.completed >= status.total) {
    return null;
  }

  async function dismiss() {
    setBusy(true);
    try {
      setStatus(await onboardingApi.setSetupDismissed(true));
    } catch {
      setBusy(false);
    }
  }

  const percent = Math.round((status.completed / status.total) * 100);
  const next = status.items.find((i) => !i.done);

  return (
    <div className="animate-fade-in-up mb-5 w-full max-w-md rounded-2xl border border-indigo-200 bg-indigo-50/60 p-4 text-left shadow-sm dark:border-indigo-900 dark:bg-indigo-950/30">
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="min-w-0 flex-1 text-left"
        >
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            Einrichtung: {status.completed} von {status.total} erledigt
          </p>
          {!expanded && next ? (
            <p className="truncate text-xs text-zinc-500">Als Nächstes: {next.title}</p>
          ) : null}
        </button>
        <button
          type="button"
          onClick={dismiss}
          disabled={busy}
          className="shrink-0 text-xs text-zinc-500 underline-offset-2 hover:underline disabled:opacity-50"
        >
          Ausblenden
        </button>
      </div>

      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-indigo-100 dark:bg-indigo-900/60" aria-hidden>
        <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${percent}%` }} />
      </div>

      {expanded ? (
        <ul className="mt-3 flex flex-col gap-1">
          {status.items.map((item) => {
            const href = item.href ?? `/settings?tab=${item.settings_tab}`;
            return (
              <li key={item.key}>
                <Link
                  href={href}
                  className={`flex items-start gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/70 dark:hover:bg-zinc-900/60 ${
                    item.done ? "opacity-60" : ""
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px] ${
                      item.done
                        ? "border-emerald-500 bg-emerald-500 text-white"
                        : "border-zinc-400 dark:border-zinc-600"
                    }`}
                    aria-hidden
                  >
                    {item.done ? "✓" : ""}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={`block text-sm text-zinc-900 dark:text-zinc-100 ${item.done ? "line-through" : ""}`}
                    >
                      {item.title}
                      <span className="sr-only">{item.done ? " (erledigt)" : " (offen)"}</span>
                    </span>
                    {!item.done ? <span className="block text-xs text-zinc-500">{item.description}</span> : null}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
