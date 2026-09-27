"use client";

export interface ToastItem {
  id: string;
  title: string;
  body?: string;
  action?: { label: string; onClick: () => void };
}

/**
 * macOS Notification Center-style banners, top-right of the viewport — bigger and more
 * prominent than a nav-bar badge, per the explicit "wie bei einem Mac... rechts in der Ecke"
 * ask. Generic (title/body/optional action), not timer-specific, so other features (proactive
 * agent messages, suggestion-ready alerts, ...) can reuse it later without a new component.
 */
export function NotificationToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="animate-toast-in rounded-xl border border-zinc-200 bg-white/95 p-4 shadow-xl backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/95"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5 min-w-0">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500 text-white">
                <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
                  <circle cx="12" cy="13" r="8" stroke="currentColor" strokeWidth={2} />
                  <path d="M12 9v4l3 2M9 2h6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
                </svg>
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{toast.title}</p>
                {toast.body ? (
                  <p className="mt-0.5 text-sm text-zinc-600 dark:text-zinc-400">{toast.body}</p>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              aria-label="Schließen"
              className="shrink-0 rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
            >
              <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
              </svg>
            </button>
          </div>
          {toast.action ? (
            <button
              type="button"
              onClick={toast.action.onClick}
              className="mt-2 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {toast.action.label}
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}
