"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { useAuth } from "@/lib/auth-context";
import { getExistingSubscription, isPushSupported, subscribeToPush, unsubscribeFromPush } from "@/lib/push";

type PushState = "checking" | "unsupported" | "subscribed" | "unsubscribed";

function PushNotificationsCard() {
  const [state, setState] = useState<PushState>("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!isPushSupported()) {
      setState("unsupported");
      return;
    }
    getExistingSubscription()
      .then((sub) => setState(sub ? "subscribed" : "unsubscribed"))
      .catch(() => setState("unsubscribed"));
  }, []);

  useEffect(() => {
    void (async () => {
      refresh();
    })();
  }, [refresh]);

  async function handleToggle() {
    setError(null);
    setBusy(true);
    try {
      if (state === "subscribed") {
        await unsubscribeFromPush();
      } else {
        await subscribeToPush();
      }
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Aktion fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  if (state === "unsupported") {
    return (
      <p className="mt-3 text-xs text-zinc-400">
        Push-Benachrichtigungen werden von diesem Browser nicht unterstützt.
      </p>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Push-Benachrichtigungen</p>
          <p className="mt-0.5 text-xs text-zinc-500">
            Der Assistent kann dich proaktiv benachrichtigen (z.B. wenn ein Timer abläuft oder ein
            Vorschlag erkannt wird), auch wenn die App nicht offen ist.
          </p>
        </div>
        <button
          type="button"
          onClick={handleToggle}
          disabled={busy || state === "checking"}
          className="shrink-0 rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {state === "checking" ? "..." : state === "subscribed" ? "Deaktivieren" : "Aktivieren"}
        </button>
      </div>
      <ErrorMessage message={error} />
      <p className="mt-2 text-xs text-zinc-400">
        Auf dem iPhone/iPad funktioniert das nur, wenn diese Seite über &quot;Zum Home-Bildschirm
        hinzufügen&quot; installiert wurde — Safari selbst liefert Push nicht an offene Tabs im
        Hintergrund (Einschränkung von iOS, nicht von OwnAI).
      </p>
    </div>
  );
}

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
      <PushNotificationsCard />
      <p className="mt-3 text-xs text-zinc-400">
        Eine eigene E-Mail-Adresse für den Assistenten kannst du im Tab &quot;E-Mail&quot; hinterlegen.
      </p>
    </div>
  );
}
