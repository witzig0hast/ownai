"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ComponentType } from "react";
import { AppShell } from "@/components/AppShell";
import { CalendarTab } from "@/components/settings/CalendarTab";
import { ContactsTab } from "@/components/settings/ContactsTab";
import { ExpensesTab } from "@/components/settings/ExpensesTab";
import { ListsTab } from "@/components/settings/ListsTab";
import { RemindersTab } from "@/components/settings/RemindersTab";
import { WeatherTab } from "@/components/settings/WeatherTab";

// Your own day-to-day data - reachable from the Übersicht cards. These used to be settings tabs,
// but a shopping list or this month's expenses are things you look at, not configuration.
const OVERVIEW_SECTIONS: Record<string, { label: string; component: ComponentType }> = {
  calendar: { label: "Kalender", component: CalendarTab },
  lists: { label: "Listen", component: ListsTab },
  reminders: { label: "Erinnerungen", component: RemindersTab },
  expenses: { label: "Ausgaben", component: ExpensesTab },
  contacts: { label: "Kontakte", component: ContactsTab },
  weather: { label: "Wetter", component: WeatherTab },
};

export default function OverviewSectionPage() {
  const { section } = useParams<{ section: string }>();
  const entry = OVERVIEW_SECTIONS[section];

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto w-full max-w-3xl">
          <Link
            href="/overview"
            className="mb-3 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            <span aria-hidden>‹</span> Übersicht
          </Link>
          {entry ? (
            <>
              <h1 className="mb-4 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
                {entry.label}
              </h1>
              <entry.component />
            </>
          ) : (
            <p className="text-sm text-zinc-500">Diesen Bereich gibt es nicht.</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
