"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { NotificationToastStack, type ToastItem } from "@/components/NotificationToast";
import * as timersApi from "@/lib/api/timers";
import type { Timer } from "@/lib/types";

const POLL_INTERVAL_MS = 20000;
const TICK_INTERVAL_MS = 1000;
const TOAST_AUTO_DISMISS_MS = 15000;

function remainingSeconds(timer: Timer): number {
  return Math.max(0, Math.floor((new Date(timer.ends_at).getTime() - Date.now()) / 1000));
}

function formatRemaining(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** A short, synthesized beep - no audio asset needed, works even if the tab has never played sound before. */
function playAlertSound(): void {
  try {
    const AudioContextClass = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new AudioContextClass();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.6);
  } catch {
    // best-effort only - a missing beep shouldn't break the timer alert
  }
}

/**
 * Small "oben rechts in der Ecke" countdown badge, shown in the nav bar on every authenticated
 * page (see AppShell/NavBar) - polls GET /timers (picks up timers set from any device/via chat)
 * and ticks the nearest one down locally each second. On expiry: a short beep, a browser
 * notification if permitted, and a visible alert state until dismissed/cancelled.
 *
 * Deliberately client-only, no server push: this only fires while the tab is open, which is an
 * accepted limitation of a self-hosted setup with no push infrastructure (see Android's
 * AlarmManager-based approach for the "works even if the app isn't open" case).
 */
export function TimerBadge() {
  const [timers, setTimers] = useState<Timer[]>([]);
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const alertedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {
        // best-effort only
      });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const poll = () => {
      timersApi
        .listTimers()
        .then((list) => {
          if (!cancelled) setTimers(list);
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

  useEffect(() => {
    const interval = setInterval(() => setTick((n) => n + 1), TICK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleDismiss = useCallback(
    async (id: string) => {
      dismissToast(id);
      setTimers((prev) => prev.filter((t) => t.id !== id));
      try {
        await timersApi.cancelTimer(id);
      } catch {
        // already removed locally; a stray server-side row isn't worth surfacing an error for
      }
    },
    [dismissToast],
  );

  useEffect(() => {
    for (const timer of timers) {
      if (remainingSeconds(timer) <= 0 && !alertedRef.current.has(timer.id)) {
        alertedRef.current.add(timer.id);
        playAlertSound();
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          try {
            new Notification("Timer abgelaufen", { body: timer.label ?? "Dein Timer ist abgelaufen." });
          } catch {
            // best-effort only
          }
        }
        setToasts((prev) => [
          ...prev,
          {
            id: timer.id,
            title: "Timer abgelaufen",
            body: timer.label ?? undefined,
            action: { label: "Beenden", onClick: () => handleDismiss(timer.id) },
          },
        ]);
        setTimeout(() => dismissToast(timer.id), TOAST_AUTO_DISMISS_MS);
      }
    }
    // `tick` isn't read here, but it's what makes an already-listed timer's expiry get noticed
    // a second after it happens rather than only on the next 20s poll.
  }, [timers, tick, handleDismiss, dismissToast]);

  if (timers.length === 0) {
    return <NotificationToastStack toasts={toasts} onDismiss={dismissToast} />;
  }

  const sorted = [...timers].sort((a, b) => remainingSeconds(a) - remainingSeconds(b));
  const nearest = sorted[0];
  const nearestExpired = remainingSeconds(nearest) <= 0;

  return (
    <div className="relative">
      <NotificationToastStack toasts={toasts} onDismiss={dismissToast} />
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
          nearestExpired
            ? "animate-pulse border-red-300 bg-red-50 text-red-600 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            : "border-zinc-300 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        }`}
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
          <circle cx="12" cy="13" r="8" stroke="currentColor" strokeWidth={2} />
          <path d="M12 9v4l3 2M9 2h6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
        </svg>
        {nearestExpired ? "Abgelaufen" : formatRemaining(remainingSeconds(nearest))}
        {timers.length > 1 ? ` (+${timers.length - 1})` : ""}
      </button>

      {open ? (
        <div className="absolute right-0 z-10 mt-2 w-64 rounded-lg border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
          <ul className="flex flex-col gap-1">
            {sorted.map((timer) => {
              const expired = remainingSeconds(timer) <= 0;
              return (
                <li
                  key={timer.id}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate text-zinc-800 dark:text-zinc-200">{timer.label ?? "Timer"}</p>
                    <p className={`text-xs ${expired ? "font-medium text-red-600 dark:text-red-400" : "text-zinc-500"}`}>
                      {expired ? "Abgelaufen" : formatRemaining(remainingSeconds(timer))}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDismiss(timer.id)}
                    className="shrink-0 rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
                    aria-label="Timer beenden"
                  >
                    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
                      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
                    </svg>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
