"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { TimerBadge } from "@/components/TimerBadge";
import * as devicesApi from "@/lib/api/devices";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "/voice", label: "Voice" },
  { href: "/chat", label: "Chat" },
  { href: "/settings", label: "Settings" },
];

function Logo() {
  return (
    <svg viewBox="0 0 24 24" className="h-8 w-8 shrink-0 transition-transform group-hover:scale-105" aria-hidden="true">
      <rect width="24" height="24" rx="7" className="fill-zinc-900 dark:fill-zinc-100" />
      <circle cx="10.5" cy="10.8" r="4" className="fill-white dark:fill-zinc-900" />
      <circle cx="15.8" cy="16" r="1.8" className="fill-indigo-500" />
    </svg>
  );
}

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
      {open ? (
        <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      ) : (
        <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      )}
    </svg>
  );
}

export function NavBar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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

  const links = [
    ...LINKS.slice(0, 2),
    ...(hasAndroidDevice ? [{ href: "/suggestions", label: "Suggestions" }] : []),
    ...LINKS.slice(2),
    ...(user?.is_admin ? [{ href: "/admin", label: "Admin" }] : []),
  ];

  return (
    <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="flex items-center justify-between px-4 py-3 sm:px-5">
        <div className="flex items-center gap-7">
          <Link href="/voice" className="group flex items-center gap-2.5">
            <Logo />
            <span className="text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              OwnAI
            </span>
          </Link>
          {/* Full link row on wider screens; collapses into the hamburger menu below md. */}
          <nav className="hidden items-center gap-1 md:flex">
            {links.map((link) => {
              const active = pathname === link.href || pathname?.startsWith(`${link.href}/`);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-all ${
                    active
                      ? "bg-indigo-500 text-white shadow-sm shadow-indigo-500/30"
                      : "text-zinc-600 hover:scale-105 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <TimerBadge />
          {user ? (
            <span className="hidden text-sm text-zinc-500 sm:inline">{user.display_name}</span>
          ) : null}
          <button
            type="button"
            onClick={logout}
            className="hidden rounded-full border border-zinc-300 px-4 py-1.5 text-sm font-medium text-zinc-700 transition-all hover:scale-105 hover:bg-zinc-100 sm:inline-block dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Log out
          </button>
          <button
            type="button"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label={mobileMenuOpen ? "Menü schließen" : "Menü öffnen"}
            aria-expanded={mobileMenuOpen}
            className="rounded-full p-2 text-zinc-600 transition-all hover:scale-110 hover:bg-zinc-100 active:scale-95 md:hidden dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            <MenuIcon open={mobileMenuOpen} />
          </button>
        </div>
      </div>

      {mobileMenuOpen ? (
        <nav className="animate-slide-down flex flex-col gap-1 border-t border-zinc-200 px-4 py-2 md:hidden dark:border-zinc-800">
          {links.map((link) => {
            const active = pathname === link.href || pathname?.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`rounded-xl px-3 py-2 text-sm font-medium transition-all ${
                  active
                    ? "bg-indigo-500 text-white"
                    : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <button
            type="button"
            onClick={logout}
            className="mt-1 rounded-xl border border-zinc-300 px-3 py-2 text-left text-sm font-medium text-zinc-700 transition-all hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Log out
          </button>
        </nav>
      ) : null}
    </header>
  );
}
