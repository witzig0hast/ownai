"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
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

const INPUT_CLASS =
  "w-full rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900";

function ProfileCard() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.display_name ?? "");
  const [city, setCity] = useState(user?.home_city ?? "");
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);

  const dirty = name.trim() !== (user?.display_name ?? "") || city.trim() !== (user?.home_city ?? "");

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    setState("saving");
    try {
      await authApi.updateMe({ display_name: name.trim(), home_city: city.trim() });
      await refreshUser();
      setState("saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
      setState("idle");
    }
  }

  return (
    <form
      onSubmit={save}
      className="animate-fade-in-up flex flex-col gap-3 rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800"
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-xs font-medium text-zinc-400">Name</span>
        <input value={name} onChange={(e) => { setName(e.target.value); setState("idle"); }} className={INPUT_CLASS} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-xs font-medium text-zinc-400">Wohnort (für Wetter und Briefing)</span>
        <input
          value={city}
          onChange={(e) => { setCity(e.target.value); setState("idle"); }}
          placeholder="z.B. Berlin"
          className={INPUT_CLASS}
        />
      </label>
      <div className="text-sm">
        <p className="text-xs font-medium text-zinc-400">E-Mail</p>
        <p className="text-zinc-900 dark:text-zinc-100">
          {user?.email}
          {user?.is_admin ? <span className="ml-2 text-xs text-indigo-500">Administrator</span> : null}
        </p>
      </div>
      <ErrorMessage message={error} />
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!dirty || state === "saving" || !name.trim()}
          className="rounded-full bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-all hover:scale-105 active:scale-95 disabled:opacity-40 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {state === "saving" ? "Speichere..." : "Speichern"}
        </button>
        {state === "saved" && !dirty ? <span className="text-xs text-emerald-600">Gespeichert.</span> : null}
      </div>
    </form>
  );
}

function pad(n: number): string {
  return n.toString().padStart(2, "0");
}

function BriefingCard() {
  const { user, refreshUser } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function update(patch: authApi.UserUpdate) {
    setError(null);
    setBusy(true);
    try {
      await authApi.updateMe(patch);
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;
  const timeValue = `${pad(user.briefing_hour)}:${pad(user.briefing_minute)}`;

  return (
    <div className="animate-fade-in-up mt-4 rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Morgen-Briefing</p>
          <p className="mt-0.5 text-xs text-zinc-500">
            Jeden Tag eine Push-Nachricht mit Terminen, Wetter, Erinnerungen und Geburtstagen. Auf der
            Übersicht kannst du es dir jederzeit auch vorlesen lassen.
          </p>
        </div>
        <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
          <input
            type="checkbox"
            checked={user.briefing_enabled}
            disabled={busy}
            onChange={(e) => update({ briefing_enabled: e.target.checked })}
            className="h-5 w-5 accent-indigo-500"
          />
          An
        </label>
      </div>
      {user.briefing_enabled ? (
        <label className="mt-3 flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
          Um
          <input
            type="time"
            value={timeValue}
            disabled={busy}
            onChange={(e) => {
              const [h, m] = e.target.value.split(":").map(Number);
              if (!Number.isNaN(h) && !Number.isNaN(m)) void update({ briefing_hour: h, briefing_minute: m });
            }}
            className="rounded-xl border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
          Uhr
        </label>
      ) : null}
      {user.briefing_enabled ? (
        <p className="mt-2 text-xs text-zinc-400">Kommt nur an, wenn Push-Benachrichtigungen (oben) auf diesem Gerät aktiv sind.</p>
      ) : null}
      <ErrorMessage message={error} />
    </div>
  );
}

export function AccountTab() {
  return (
    <div className="max-w-md">
      <ProfileCard />
      <PushNotificationsCard />
      <BriefingCard />
      <SsoCard />
      <p className="mt-3 text-xs text-zinc-400">
        Eine eigene E-Mail-Adresse für den Assistenten kannst du unter{" "}
        <Link href="/settings?tab=email" className="underline">
          E-Mail
        </Link>{" "}
        hinterlegen.
      </p>
    </div>
  );
}
