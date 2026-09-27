"use client";

import { useState, type ComponentType } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { AccountTab } from "@/components/settings/AccountTab";
import { AgentBusTab } from "@/components/settings/AgentBusTab";
import { CalendarTab } from "@/components/settings/CalendarTab";
import { EmailTab } from "@/components/settings/EmailTab";
import { IntegrationsTab } from "@/components/settings/IntegrationsTab";

type SettingsTab = "integrations" | "calendar" | "email" | "agent-bus" | "account";

const TAB_COMPONENTS: Record<SettingsTab, ComponentType> = {
  integrations: IntegrationsTab,
  calendar: CalendarTab,
  email: EmailTab,
  "agent-bus": AgentBusTab,
  account: AccountTab,
};

const TABS: { key: SettingsTab; label: string }[] = [
  { key: "integrations", label: "Integrations" },
  { key: "calendar", label: "Kalender" },
  { key: "email", label: "E-Mail" },
  { key: "agent-bus", label: "Agent Bus" },
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
