"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { AccountTab } from "@/components/settings/AccountTab";
import { AgentBusTab } from "@/components/settings/AgentBusTab";
import { EmailTab } from "@/components/settings/EmailTab";
import { IntegrationsTab } from "@/components/settings/IntegrationsTab";

type SettingsTab = "integrations" | "email" | "agent-bus" | "account";

const TABS: { key: SettingsTab; label: string }[] = [
  { key: "integrations", label: "Integrations" },
  { key: "email", label: "E-Mail" },
  { key: "agent-bus", label: "Agent Bus" },
  { key: "account", label: "Konto" },
];

export default function SettingsPage() {
  const [tab, setTab] = useState<SettingsTab>("integrations");

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4">
        <PageHeader title="Settings" />

        <div className="mb-5 flex gap-1 border-b border-zinc-200 dark:border-zinc-800">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                  : "border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "integrations" ? (
          <IntegrationsTab />
        ) : tab === "email" ? (
          <EmailTab />
        ) : tab === "agent-bus" ? (
          <AgentBusTab />
        ) : (
          <AccountTab />
        )}
      </div>
    </AppShell>
  );
}
