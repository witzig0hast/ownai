"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import * as authApi from "@/lib/api/auth";
import { ApiError } from "@/lib/api-client";
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
    <div className="animate-fade-in-up mt-4 rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
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
          className="shrink-0 rounded-full bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-all hover:scale-105 hover:bg-zinc-700 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
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

type SsoState = "checking" | "unavailable" | "ready";

function SsoCard() {
  const { user, refreshUser } = useAuth();
  const [state, setState] = useState<SsoState>("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const { enabled } = await authApi.ssoStatus();
        setState(enabled ? "ready" : "unavailable");
      } catch {
        setState("unavailable");
      }
    })();
  }, []);

  async function handleLink() {
    setError(null);
    setBusy(true);
    try {
      const { url } = await authApi.ssoLinkUrl();
      // Full-page navigation, not a client-side route - the next stop is the SSO provider
      // itself, outside this app entirely (see lib/api/auth.ts's ssoLinkUrl()).
      window.location.href = url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verknüpfung konnte nicht gestartet werden.");
      setBusy(false);
    }
  }

  async function handleUnlink() {
    if (!window.confirm("SSO-Verknüpfung wirklich trennen? Du kannst dich danach nur noch mit Passwort anmelden.")) {
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await authApi.ssoUnlink();
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Trennen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  if (state === "checking" || state === "unavailable") {
    return null;
  }

  return (
    <div className="animate-fade-in-up mt-4 rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Single Sign-On</p>
          <p className="mt-0.5 text-xs text-zinc-500">
            {user?.sso_linked
              ? "Dieses Konto ist mit deinem SSO-Provider verknüpft - Login ist auch darüber möglich."
              : "Verknüpfe dieses Konto mit deinem SSO-Provider, um dich künftig darüber anzumelden."}
          </p>
        </div>
        <button
          type="button"
          onClick={user?.sso_linked ? handleUnlink : handleLink}
          disabled={busy}
          className="shrink-0 rounded-full bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-all hover:scale-105 hover:bg-zinc-700 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? "..." : user?.sso_linked ? "Trennen" : "Verknüpfen"}
        </button>
      </div>
      <ErrorMessage message={error} />
    </div>
  );
}

export function AccountTab() {
  const { user } = useAuth();

  return (
    <div className="max-w-md">
      <p className="mb-4 text-sm text-zinc-500">Dein Konto.</p>
      <div className="animate-fade-in-up rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
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
      <SsoCard />
      <p className="mt-3 text-xs text-zinc-400">
        Eine eigene E-Mail-Adresse für den Assistenten kannst du im Tab &quot;E-Mail&quot; hinterlegen.
      </p>
    </div>
  );
}
