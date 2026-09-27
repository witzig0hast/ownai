"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { TimerBadge } from "@/components/TimerBadge";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "/voice", label: "Voice" },
  { href: "/chat", label: "Chat" },
  { href: "/calendar", label: "Calendar" },
  { href: "/suggestions", label: "Suggestions" },
  { href: "/integrations", label: "Integrations" },
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

export function NavBar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-zinc-200 bg-white/80 px-5 py-3 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/80">
      <div className="flex items-center gap-7">
        <Link href="/voice" className="flex items-center gap-2">
          <Logo />
          <span className="text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            OwnAI
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {LINKS.map((link) => {
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
      <div className="flex items-center gap-3">
        <TimerBadge />
        {user ? (
          <span className="hidden text-sm text-zinc-500 sm:inline">{user.display_name}</span>
        ) : null}
        <button
          type="button"
          onClick={logout}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
