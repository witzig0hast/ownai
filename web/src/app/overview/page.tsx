"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { SetupChecklist } from "@/components/SetupChecklist";
import { ApiError } from "@/lib/api-client";
import * as authApi from "@/lib/api/auth";
import * as listsApi from "@/lib/api/lists";
import * as overviewApi from "@/lib/api/overview";
import type { Overview, OverviewList } from "@/lib/api/overview";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/format";
import { speakAndWait, stopSpeaking, unlockSpeech } from "@/lib/tts";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Gute Nacht";
  if (h < 11) return "Guten Morgen";
  if (h < 18) return "Hallo";
  return "Guten Abend";
}

function euro(amount: number): string {
  return amount.toLocaleString("de-DE", { style: "currency", currency: "EUR" });
}

function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

function Card({
  title,
  href,
  linkLabel = "Alle",
  children,
  delay = 0,
}: {
  title: string;
  href?: string;
  linkLabel?: string;
  children: ReactNode;
  delay?: number;
}) {
  return (
    <section
      style={{ animationDelay: `${delay}ms` }}
      className="animate-fade-in-up mb-4 flex break-inside-avoid flex-col rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{title}</h2>
        {href ? (
          <Link href={href} className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400">
            {linkLabel}
          </Link>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-2 text-sm">{children}</div>
    </section>
  );
}

function Muted({ children }: { children: ReactNode }) {
  return <p className="text-sm text-zinc-500">{children}</p>;
}

function ListBlock({ list, onChanged }: { list: OverviewList; onChanged: () => void }) {
  const [items, setItems] = useState(list.open_items);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  async function check(itemId: string) {
    setItems((prev) => prev.filter((i) => i.id !== itemId));
    try {
      await listsApi.updateItem(list.id, itemId, { done: true });
    } finally {
      onChanged();
    }
  }

  async function add(e: FormEvent) {
    e.preventDefault();
    const content = draft.trim();
    if (!content) return;
    setBusy(true);
    try {
      const updated = await listsApi.addItem(list.id, content);
      setItems(updated.items.filter((i) => !i.done).map((i) => ({ id: i.id, content: i.content })).slice(0, 6));
      setDraft("");
    } finally {
      setBusy(false);
    }
  }

  const hidden = Math.max(0, list.open_count - items.length);

  return (
    <div className="rounded-xl bg-zinc-50 p-3 dark:bg-zinc-900/60">
      <p className="mb-1.5 flex items-center justify-between text-xs font-semibold tracking-wide text-zinc-500 uppercase">
        <span>
          {list.kind === "shopping" ? "🛒 " : ""}
          {list.name}
        </span>
        <span className="font-normal normal-case">{items.length + hidden} offen</span>
      </p>
      {items.length === 0 && hidden === 0 ? <p className="text-xs text-zinc-500">Alles erledigt.</p> : null}
      <ul className="flex flex-col">
        {items.map((item) => (
          <li key={item.id}>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg px-1 py-1 hover:bg-white dark:hover:bg-zinc-800">
              <input type="checkbox" onChange={() => check(item.id)} className="h-4 w-4 accent-indigo-500" />
              <span className="min-w-0 truncate">{item.content}</span>
            </label>
          </li>
        ))}
      </ul>
      {hidden > 0 ? <p className="mt-1 px-1 text-xs text-zinc-500">+ {hidden} weitere</p> : null}
      <form onSubmit={add} className="mt-1.5 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Hinzufügen..."
          aria-label={`Zu ${list.name} hinzufügen`}
          className="flex-1 rounded-lg border border-zinc-200 bg-white px-2 py-1 text-sm focus:border-indigo-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={busy || !draft.trim()}
          className="rounded-lg bg-zinc-900 px-2.5 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
          aria-label="Hinzufügen"
        >
          +
        </button>
      </form>
    </div>
  );
}

function HomeCityForm({ onSaved }: { onSaved: () => void }) {
  const { refreshUser } = useAuth();
  const [city, setCity] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!city.trim()) return;
    setBusy(true);
    try {
      await authApi.updateMe({ home_city: city.trim() });
      await refreshUser();
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-2">
      <Muted>Für welchen Ort soll das Wetter angezeigt werden?</Muted>
      <div className="flex gap-2">
        <input
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="z.B. Berlin"
          aria-label="Wohnort"
          className="flex-1 rounded-lg border border-zinc-300 px-2.5 py-1.5 text-sm focus:border-indigo-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={busy || !city.trim()}
          className="rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Speichern
        </button>
      </div>
    </form>
  );
}

function BriefingButton() {
  const [state, setState] = useState<"idle" | "loading" | "speaking">("idle");
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    if (state === "speaking") {
      stopSpeaking();
      setState("idle");
      return;
    }
    unlockSpeech(); // must run inside the click handler (see tts.ts)
    setError(null);
    setState("loading");
    try {
      const text = await overviewApi.getBriefing();
      setState("speaking");
      await speakAndWait(text);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Briefing konnte nicht geladen werden.");
    } finally {
      setState("idle");
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={toggle}
        disabled={state === "loading"}
        className="flex items-center gap-2 rounded-full bg-indigo-500 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-indigo-500/30 transition-all hover:scale-105 hover:bg-indigo-600 active:scale-95 disabled:opacity-60"
      >
        <span aria-hidden>{state === "speaking" ? "■" : "▶"}</span>
        {state === "loading" ? "Lade..." : state === "speaking" ? "Stopp" : "Tagesbriefing vorlesen"}
      </button>
      {error ? <p className="text-xs text-red-600">{error}</p> : null}
    </div>
  );
}

function OverviewContent() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await overviewApi.getOverview());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Übersicht konnte nicht geladen werden.");
    }
  }, []);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const todayLabel = new Date().toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="mx-auto w-full max-w-6xl">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-zinc-500">{todayLabel}</p>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            {greeting()}
            {data ? `, ${data.display_name}` : ""}
          </h1>
        </div>
        <BriefingButton />
      </div>

      <SetupChecklist />
      <ErrorMessage message={error} />

      {data && data.pending_actions > 0 ? (
        <p className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
          {data.pending_actions === 1 ? "1 Aktion wartet" : `${data.pending_actions} Aktionen warten`} auf deine
          Bestätigung — oben über das Glocken-Symbol öffnen.
        </p>
      ) : null}

      {!data && !error ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-shimmer h-40 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {data ? (
        // CSS columns rather than a grid: cards differ a lot in height (a long list vs. "no events"),
        // and a grid row would leave a hole next to the tallest card.
        <div className="gap-4 md:columns-2 xl:columns-3">
          <Card title="Heute" href="/overview/calendar" linkLabel="Kalender">
            {!data.calendar.connected ? (
              <Muted>
                Kein Kalender verbunden.{" "}
                <Link href="/settings?tab=integrations" className="text-indigo-600 underline dark:text-indigo-400">
                  Jetzt verbinden
                </Link>
              </Muted>
            ) : data.calendar.error ? (
              <p className="text-sm text-red-600 dark:text-red-400">Kalender nicht erreichbar: {data.calendar.error}</p>
            ) : data.calendar.events.length === 0 ? (
              <Muted>Keine Termine heute.</Muted>
            ) : (
              <ul className="flex flex-col gap-2">
                {data.calendar.events.map((e, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="w-12 shrink-0 font-medium text-zinc-900 tabular-nums dark:text-zinc-100">
                      {e.all_day ? "ganztg." : clock(e.start)}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-zinc-900 dark:text-zinc-100">{e.title}</span>
                      {e.location ? <span className="block truncate text-xs text-zinc-500">{e.location}</span> : null}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Wetter" href="/overview/weather" linkLabel="Vorhersage" delay={40}>
            {!data.weather.home_city ? (
              <HomeCityForm onSaved={load} />
            ) : data.weather.error ? (
              <p className="text-sm text-red-600 dark:text-red-400">{data.weather.error}</p>
            ) : data.weather.data ? (
              <div>
                <div className="flex items-baseline gap-3">
                  <span className="text-4xl font-semibold text-zinc-900 tabular-nums dark:text-zinc-100">
                    {Math.round(data.weather.data.current_temperature)}°
                  </span>
                  <span className="text-zinc-600 dark:text-zinc-400">{data.weather.data.current_condition}</span>
                </div>
                <p className="text-xs text-zinc-500">{data.weather.data.location}</p>
                <ul className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  {data.weather.data.daily.slice(0, 3).map((d, i) => (
                    <li key={d.date} className="rounded-lg bg-zinc-50 px-1 py-2 dark:bg-zinc-900/60">
                      <p className="font-medium text-zinc-700 dark:text-zinc-300">
                        {i === 0 ? "Heute" : new Date(d.date).toLocaleDateString("de-DE", { weekday: "short" })}
                      </p>
                      <p className="tabular-nums text-zinc-900 dark:text-zinc-100">
                        {Math.round(d.temp_min)}° / {Math.round(d.temp_max)}°
                      </p>
                      <p className="truncate text-zinc-500">{d.condition}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </Card>

          <Card title="Listen" href="/overview/lists" delay={80}>
            {data.lists.length === 0 ? (
              <Muted>
                Noch keine Listen. Sag z.B. „Setz Milch auf die Einkaufsliste“ oder{" "}
                <Link href="/overview/lists" className="text-indigo-600 underline dark:text-indigo-400">
                  leg eine an
                </Link>
                .
              </Muted>
            ) : (
              data.lists.slice(0, 3).map((list) => <ListBlock key={list.id} list={list} onChanged={load} />)
            )}
          </Card>

          <Card title="Erinnerungen" href="/overview/reminders" delay={120}>
            {data.reminders.length === 0 ? (
              <Muted>Keine Erinnerungen. Z.B. „Erinnere mich jeden Montag um 19 Uhr an den Müll“.</Muted>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {data.reminders.map((r) => (
                  <li key={r.id} className="flex justify-between gap-3">
                    <span className="min-w-0 truncate text-zinc-900 dark:text-zinc-100">{r.label}</span>
                    <span className="shrink-0 text-xs text-zinc-500">{formatDateTime(r.next_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Geburtstage" href="/overview/contacts" linkLabel="Kontakte" delay={160}>
            {data.birthdays.length === 0 ? (
              <Muted>In den nächsten 30 Tagen keine Geburtstage.</Muted>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {data.birthdays.map((b) => (
                  <li key={b.contact_id} className="flex justify-between gap-3">
                    <span className="min-w-0 truncate text-zinc-900 dark:text-zinc-100">
                      {b.name}
                      {b.turns ? <span className="text-zinc-500"> · wird {b.turns}</span> : null}
                    </span>
                    <span
                      className={`shrink-0 text-xs ${b.days_until === 0 ? "font-semibold text-indigo-600 dark:text-indigo-400" : "text-zinc-500"}`}
                    >
                      {b.days_until === 0 ? "heute 🎉" : b.days_until === 1 ? "morgen" : `in ${b.days_until} Tagen`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Ausgaben diesen Monat" href="/overview/expenses" linkLabel="Details" delay={200}>
            <p className="text-3xl font-semibold text-zinc-900 tabular-nums dark:text-zinc-100">
              {euro(data.expenses.month_total)}
            </p>
            <p className="text-xs text-zinc-500">
              {data.expenses.count === 1 ? "1 Ausgabe" : `${data.expenses.count} Ausgaben`}
            </p>
            {data.expenses.by_category.length > 0 ? (
              <ul className="mt-2 flex flex-col gap-1.5">
                {data.expenses.by_category.slice(0, 4).map((c) => (
                  <li key={c.category} className="text-xs">
                    <div className="mb-0.5 flex justify-between">
                      <span className="text-zinc-700 dark:text-zinc-300">{c.category}</span>
                      <span className="text-zinc-500 tabular-nums">{euro(c.total)}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                      <div
                        className="h-full rounded-full bg-indigo-500"
                        style={{ width: `${(c.total / data.expenses.month_total) * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </Card>
        </div>
      ) : null}
    </div>
  );
}

export default function OverviewPage() {
  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <OverviewContent />
      </div>
    </AppShell>
  );
}
