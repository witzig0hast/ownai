"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { TimerBadge } from "@/components/TimerBadge";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "/voice", label: "Voice" },
  { href: "/chat", label: "Chat" },
  { href: "/calendar", label: "Calendar" },
  { href: "/suggestions", label: "Suggestions" },
  { href: "/settings", label: "Settings" },
];

function Logo() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6 shrink-0" aria-hidden="true">
      <rect width="24" height="24" rx="6" className="fill-zinc-900 dark:fill-zinc-100" />
      <circle cx="10.5" cy="10.8" r="4" className="fill-white dark:fill-zinc-900" />
      <circle cx="15.8" cy="16" r="1.8" className="fill-indigo-500" />
    </svg>
  );
}

function MenuIcon({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
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

  const links = user?.is_admin ? [...LINKS, { href: "/admin", label: "Admin" }] : LINKS;

  return (
    <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="flex items-center justify-between px-4 py-3 sm:px-5">
        <div className="flex items-center gap-7">
          <Link href="/voice" className="flex items-center gap-2">
            <Logo />
            <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
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
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    active
                      ? "bg-indigo-500 text-white"
                      : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
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
            className="hidden rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 sm:inline-block dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Log out
          </button>
          <button
            type="button"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label={mobileMenuOpen ? "Menü schließen" : "Menü öffnen"}
            aria-expanded={mobileMenuOpen}
            className="rounded-md p-1.5 text-zinc-600 transition-colors hover:bg-zinc-100 md:hidden dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            <MenuIcon open={mobileMenuOpen} />
          </button>
        </div>
      </div>

      {mobileMenuOpen ? (
        <nav className="flex flex-col gap-1 border-t border-zinc-200 px-4 py-2 md:hidden dark:border-zinc-800">
          {links.map((link) => {
            const active = pathname === link.href || pathname?.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
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
            className="mt-1 rounded-md border border-zinc-300 px-3 py-2 text-left text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Log out
          </button>
        </nav>
      ) : null}
    </header>
  );
}
