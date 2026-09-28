"use client";

import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/**
 * A small centered popup dialog — no library, matches the app's existing minimal styling.
 * Portaled to document.body: several callers (every Settings tab) render this from inside
 * settings/page.tsx's `animate-fade-in-up` tab wrapper, whose entrance animation ends on
 * `transform: translateY(0)` and holds it via fill-mode - any non-`none` transform on an
 * ancestor (even a visual no-op like translateY(0)) makes it the containing block for
 * `position: fixed` descendants instead of the viewport. Without the portal, this modal's
 * `fixed inset-0` backdrop would size/position itself against that wrapper div's box - not
 * necessarily full-screen or centered - instead of the actual viewport.
 */
export function Modal({ title, onClose, children }: ModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Client-only flag so the first client render matches the server's (both render nothing -
    // document.body doesn't exist server-side to portal into) before flipping true - the
    // standard, necessary pattern for a portal under SSR, not one this lint rule's "avoid
    // cascading renders" concern actually applies to.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  if (!mounted) return null;

  return createPortal(
    <div
      className="animate-backdrop-in fixed inset-0 z-20 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className="animate-scale-in w-full max-w-sm rounded-3xl border border-zinc-200 bg-white p-5 shadow-2xl dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Schließen"
            className="rounded-full p-1.5 text-zinc-400 transition-all hover:scale-110 hover:bg-zinc-100 hover:text-zinc-600 active:scale-95 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
