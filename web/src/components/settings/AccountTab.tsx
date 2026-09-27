"use client";

import { useAuth } from "@/lib/auth-context";

export function AccountTab() {
  const { user } = useAuth();

  return (
    <div className="max-w-md">
      <p className="mb-4 text-sm text-zinc-500">Dein Konto.</p>
      <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        <dl className="flex flex-col gap-3 text-sm">
          <div>
            <dt className="text-xs font-medium text-zinc-400">Name</dt>
            <dd className="text-zinc-900 dark:text-zinc-100">{user?.display_name}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-zinc-400">E-Mail</dt>
            <dd className="text-zinc-900 dark:text-zinc-100">{user?.email}</dd>
          </div>
          {user?.is_admin ? (
            <div>
              <dt className="text-xs font-medium text-zinc-400">Rolle</dt>
              <dd className="text-zinc-900 dark:text-zinc-100">Administrator</dd>
            </div>
          ) : null}
        </dl>
      </div>
      <p className="mt-3 text-xs text-zinc-400">
        Weitere Einstellungen (z.B. eine eigene E-Mail-Adresse für den Assistenten) landen hier, sobald sie
        gebaut sind.
      </p>
    </div>
  );
}
