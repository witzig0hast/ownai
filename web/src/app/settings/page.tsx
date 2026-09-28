"use client";

import { useState, type ComponentType } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { AccountTab } from "@/components/settings/AccountTab";
import { AgentBusTab } from "@/components/settings/AgentBusTab";
import { AutomationsTab } from "@/components/settings/AutomationsTab";
import { CalendarTab } from "@/components/settings/CalendarTab";
import { ContactsTab } from "@/components/settings/ContactsTab";
import { EmailTab } from "@/components/settings/EmailTab";
import { ExpensesTab } from "@/components/settings/ExpensesTab";
import { IntegrationsTab } from "@/components/settings/IntegrationsTab";
import { ListsTab } from "@/components/settings/ListsTab";
import { MemoryTab } from "@/components/settings/MemoryTab";
import { PermanentAgentsTab } from "@/components/settings/PermanentAgentsTab";
import { RemindersTab } from "@/components/settings/RemindersTab";
import { RssTab } from "@/components/settings/RssTab";
import { WeatherTab } from "@/components/settings/WeatherTab";
import { WebClipperTab } from "@/components/settings/WebClipperTab";

type SettingsTab =
  | "integrations"
  | "calendar"
  | "email"
  | "agent-bus"
  | "memory"
  | "contacts"
  | "reminders"
  | "automations"
  | "lists"
  | "expenses"
  | "weather"
  | "rss"
  | "clipper"
  | "permanent-agents"
  | "account";

const TAB_COMPONENTS: Record<SettingsTab, ComponentType> = {
  integrations: IntegrationsTab,
  calendar: CalendarTab,
  email: EmailTab,
  "agent-bus": AgentBusTab,
  memory: MemoryTab,
  contacts: ContactsTab,
  reminders: RemindersTab,
  automations: AutomationsTab,
  lists: ListsTab,
  expenses: ExpensesTab,
  weather: WeatherTab,
  rss: RssTab,
  clipper: WebClipperTab,
  "permanent-agents": PermanentAgentsTab,
  account: AccountTab,
};

const TABS: { key: SettingsTab; label: string }[] = [
  { key: "integrations", label: "Integrations" },
  { key: "calendar", label: "Kalender" },
  { key: "email", label: "E-Mail" },
  { key: "agent-bus", label: "Agent Bus" },
  { key: "memory", label: "Gedächtnis" },
  { key: "contacts", label: "Kontakte" },
  { key: "reminders", label: "Erinnerungen" },
  { key: "automations", label: "Automatisierungen" },
  { key: "lists", label: "Listen" },
  { key: "expenses", label: "Ausgaben" },
  { key: "weather", label: "Wetter" },
  { key: "rss", label: "News" },
  { key: "clipper", label: "Web-Clipper" },
  { key: "permanent-agents", label: "Agenten" },
  { key: "account", label: "Konto" },
];

export default function SettingsPage() {
  const [tab, setTab] = useState<SettingsTab>("integrations");
  const ActiveTab = TAB_COMPONENTS[tab];

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4">
        <PageHeader title="Settings" />

        <div className="mb-5 flex gap-1 overflow-x-auto border-b border-zinc-200 dark:border-zinc-800">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`-mb-px shrink-0 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <ActiveTab />
      </div>
    </AppShell>
  );
}
