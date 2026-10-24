"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { PendingActionsGate } from "@/components/PendingActionsGate";
import { TimerBadge } from "@/components/TimerBadge";
import * as devicesApi from "@/lib/api/devices";
import { useAuth } from "@/lib/auth-context";

function Logo() {
  return (
    <svg viewBox="0 0 24 24" className="h-8 w-8 shrink-0 transition-transform group-hover:scale-105" aria-hidden="true">
      <rect width="24" height="24" rx="7" className="fill-zinc-900 dark:fill-zinc-100" />
      <circle cx="10.5" cy="10.8" r="4" className="fill-white dark:fill-zinc-900" />
      <circle cx="15.8" cy="16" r="1.8" className="fill-indigo-500" />
    </svg>
  );
}

const ICON = "h-6 w-6";
const STROKE = { stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={ICON} aria-hidden="true">
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" {...STROKE} />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" {...STROKE} />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" {...STROKE} />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" {...STROKE} />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={ICON} aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" {...STROKE} />
      <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" {...STROKE} />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={ICON} aria-hidden="true">
      <path d="M4 5.5h16v10H9l-5 4v-14Z" {...STROKE} />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={ICON} aria-hidden="true">
      <circle cx="5.5" cy="12" r="1.4" fill="currentColor" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
      <circle cx="18.5" cy="12" r="1.4" fill="currentColor" />
    </svg>
  );
}

function SearchIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden="true">
      <circle cx="11" cy="11" r="6.5" {...STROKE} />
      <path d="m16 16 4.5 4.5" {...STROKE} />
    </svg>
  );
}

function isActive(pathname: string | null, href: string): boolean {
  return pathname === href || !!pathname?.startsWith(`${href}/`);
}

function useSecondaryLinks() {
  const { user } = useAuth();
  // Suggestions is fed exclusively by the Android app's notification-forwarding pipeline - on a
  // web-only account it would only ever show "keine Vorschläge", so it's hidden entirely unless
  // an Android device is actually registered.
  const [hasAndroidDevice, setHasAndroidDevice] = useState(false);

  useEffect(() => {
    devicesApi
      .listDevices()
      .then((devices) => setHasAndroidDevice(devices.some((d) => d.platform === "android")))
      .catch(() => {});
  }, []);

  return [
    ...(hasAndroidDevice ? [{ href: "/suggestions", label: "Vorschläge" }] : []),
    { href: "/settings", label: "Einstellungen" },
    { href: "/help", label: "Hilfe" },
    ...(user?.is_admin ? [{ href: "/admin", label: "Admin" }] : []),
  ];
}

const PRIMARY = [
  { href: "/overview", label: "Übersicht", icon: <HomeIcon /> },
  { href: "/voice", label: "Sprechen", icon: <MicIcon /> },
  { href: "/chat", label: "Chat", icon: <ChatIcon /> },
];

function BottomTab({ href, label, icon, active, onClick }: { href?: string; label: string; icon: ReactNode; active: boolean; onClick?: () => void }) {
  const className = `flex flex-1 flex-col items-center justify-center gap-0.5 pt-2 pb-1.5 text-[11px] font-medium transition-colors ${
    active ? "text-indigo-600 dark:text-indigo-400" : "text-zinc-500 dark:text-zinc-400"
  }`;
  const content = (
    <>
      {icon}
      {label}
    </>
  );
  return href ? (
    <Link href={href} className={className} aria-current={active ? "page" : undefined}>
      {content}
    </Link>
  ) : (
    <button type="button" onClick={onClick} className={className} aria-expanded={active}>
      {content}
    </button>
  );
}

/**
 * Phones get a thumb-reachable bottom tab bar (Übersicht · Sprechen · Chat · Mehr) instead of a
 * hamburger menu - the way native apps on both platforms are navigated, and what makes the
 * installed PWA feel like an app. "Mehr" opens a sheet with the less frequent destinations.
 * Desktop keeps a single top bar with everything. AppShell reserves the bottom bar's height.
 */
export function NavBar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const secondary = useSecondaryLinks();
  const [moreOpen, setMoreOpen] = useState(false);
  const moreActive = moreOpen || secondary.some((l) => isActive(pathname, l.href)) || isActive(pathname, "/search");

  return (
    <>
      <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 pt-[env(safe-area-inset-top)] backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/80">
        <div className="flex items-center justify-between px-4 py-2.5 sm:px-5 md:py-3">
          <div className="flex items-center gap-7">
            <Link href="/overview" className="group flex items-center gap-2.5">
              <Logo />
              <span className="text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">OwnAI</span>
            </Link>
            <nav aria-label="Hauptnavigation" className="hidden items-center gap-1 md:flex">
              {[...PRIMARY, ...secondary].map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={isActive(pathname, link.href) ? "page" : undefined}
                  className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-all lg:px-4 ${
                    isActive(pathname, link.href)
                      ? "bg-indigo-500 text-white shadow-sm shadow-indigo-500/30"
                      : "text-zinc-600 hover:scale-105 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-3">
            <Link
              href="/search"
              aria-label="Suchen"
              className={`rounded-full p-2 transition-all hover:bg-zinc-100 dark:hover:bg-zinc-800 ${
                isActive(pathname, "/search") ? "text-indigo-600 dark:text-indigo-400" : "text-zinc-600 dark:text-zinc-300"
              }`}
            >
              <SearchIcon />
            </Link>
            <PendingActionsGate />
            <TimerBadge />
            {user ? <span className="hidden text-sm text-zinc-500 lg:inline">{user.display_name}</span> : null}
            <button
              type="button"
              onClick={logout}
              className="hidden rounded-full border border-zinc-300 px-4 py-1.5 text-sm font-medium text-zinc-700 transition-all hover:scale-105 hover:bg-zinc-100 md:inline-block dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              Abmelden
            </button>
          </div>
        </div>
      </header>

      {moreOpen ? (
        <div className="fixed inset-0 z-30 md:hidden" role="dialog" aria-label="Mehr">
          <button
            type="button"
            aria-label="Schließen"
            onClick={() => setMoreOpen(false)}
            className="animate-backdrop-in absolute inset-0 bg-black/30"
          />
          <nav className="animate-slide-up absolute inset-x-0 bottom-0 rounded-t-3xl bg-white px-4 pt-3 pb-[calc(5rem+env(safe-area-inset-bottom))] shadow-2xl dark:bg-zinc-950">
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-zinc-300 dark:bg-zinc-700" aria-hidden />
            {user ? <p className="mb-2 px-3 text-xs text-zinc-500">Angemeldet als {user.display_name}</p> : null}
            <ul className="flex flex-col gap-1">
              {secondary.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    onClick={() => setMoreOpen(false)}
                    className={`block rounded-xl px-3 py-3 text-base font-medium ${
                      isActive(pathname, link.href)
                        ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300"
                        : "text-zinc-800 hover:bg-zinc-100 dark:text-zinc-200 dark:hover:bg-zinc-800"
                    }`}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  onClick={logout}
                  className="mt-1 w-full rounded-xl px-3 py-3 text-left text-base font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                >
                  Abmelden
                </button>
              </li>
            </ul>
          </nav>
        </div>
      ) : null}

      <nav
        aria-label="Hauptnavigation"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-zinc-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm md:hidden dark:border-zinc-800 dark:bg-zinc-950/95"
      >
        {PRIMARY.map((tab) => (
          <BottomTab
            key={tab.href}
            href={tab.href}
            label={tab.label}
            icon={tab.icon}
            active={!moreOpen && isActive(pathname, tab.href)}
          />
        ))}
        <BottomTab label="Mehr" icon={<MoreIcon />} active={moreActive} onClick={() => setMoreOpen((v) => !v)} />
      </nav>
    </>
  );
}
