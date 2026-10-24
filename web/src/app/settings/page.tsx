"use client";

import { Suspense, useEffect, type ComponentType } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { SetupChecklist } from "@/components/SetupChecklist";
import { AccountTab } from "@/components/settings/AccountTab";
import { AgentBusTab } from "@/components/settings/AgentBusTab";
import { AutomationsTab } from "@/components/settings/AutomationsTab";
import { EmailTab } from "@/components/settings/EmailTab";
import { IntegrationsTab } from "@/components/settings/IntegrationsTab";
import { LogsTab } from "@/components/settings/LogsTab";
import { MemoryTab } from "@/components/settings/MemoryTab";
import { PermanentAgentsTab } from "@/components/settings/PermanentAgentsTab";
import { RssTab } from "@/components/settings/RssTab";
import { WebClipperTab } from "@/components/settings/WebClipperTab";

interface TabDef {
  key: string;
  label: string;
  description: string;
  component: ComponentType;
}

// Grouped into small, recognizable areas. The key is also the `?tab=` value, which the setup
// checklist and the help page link to - keep keys stable even if labels change. Day-to-day data
// (calendar, lists, reminders, expenses, contacts, weather) lives under /overview instead.
const GROUPS: { label: string; tabs: TabDef[] }[] = [
  {
    label: "Verbindungen",
    tabs: [
      { key: "integrations", label: "Dienste", description: "Kalender (CalDAV), Home Assistant und Web-Suche verbinden.", component: IntegrationsTab },
      { key: "email", label: "E-Mail", description: "Eigenes Postfach zum Senden und für eingehende Mails.", component: EmailTab },
      { key: "rss", label: "News", description: "RSS-Feeds, die der Assistent für dich zusammenfasst.", component: RssTab },
      { key: "clipper", label: "Web-Clipper", description: "Webseiten per Lesezeichen an den Assistenten schicken.", component: WebClipperTab },
    ],
  },
  {
    label: "Assistent",
    tabs: [
      { key: "memory", label: "Gedächtnis", description: "Was sich der Assistent dauerhaft über dich merkt.", component: MemoryTab },
      { key: "automations", label: "Automatisierungen", description: "Wenn-Dann-Regeln auf Basis von Home Assistant.", component: AutomationsTab },
      { key: "permanent-agents", label: "Agenten", description: "Agenten, die regelmäßig selbstständig Aufgaben erledigen.", component: PermanentAgentsTab },
      { key: "agent-bus", label: "Agent Bus", description: "Andere Programme/KIs mit deinem Assistenten sprechen lassen.", component: AgentBusTab },
    ],
  },
  {
    label: "Konto & System",
    tabs: [
      { key: "account", label: "Konto", description: "Profil, Wohnort, Morgen-Briefing, Push, Darstellung und SSO.", component: AccountTab },
      { key: "logs", label: "Logs", description: "Was im Hintergrund passiert ist - hilfreich bei Problemen.", component: LogsTab },
    ],
  },
];

// Old ?tab= links (bookmarks, older help texts) for sections that moved to the Übersicht.
const MOVED_TO_OVERVIEW = new Set(["calendar", "weather", "reminders", "contacts", "lists", "expenses"]);

const ALL_TABS = GROUPS.flatMap((g) => g.tabs);
const DEFAULT_TAB = "integrations";

function SettingsContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab");

  useEffect(() => {
    if (requested && MOVED_TO_OVERVIEW.has(requested)) router.replace(`/overview/${requested}`);
  }, [requested, router]);
  const active = ALL_TABS.find((t) => t.key === requested) ?? ALL_TABS.find((t) => t.key === DEFAULT_TAB)!;
  const ActiveTab = active.component;

  function select(key: string) {
    router.replace(`${pathname}?tab=${key}`, { scroll: false });
  }

  return (
    <div className="flex flex-col gap-5 md:flex-row md:items-start">
      {/* Phone: one compact grouped dropdown instead of a 16-pill horizontal scroller. */}
      <div className="md:hidden">
        <label htmlFor="settings-tab" className="sr-only">
          Bereich
        </label>
        <select
          id="settings-tab"
          value={active.key}
          onChange={(e) => select(e.target.value)}
          className="w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        >
          {GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.tabs.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      <nav aria-label="Einstellungen" className="hidden w-52 shrink-0 flex-col gap-4 md:flex">
        {GROUPS.map((group) => (
          <div key={group.label}>
            <p className="mb-1 px-3 text-xs font-semibold tracking-wide text-zinc-400 uppercase">{group.label}</p>
            <ul className="flex flex-col gap-0.5">
              {group.tabs.map((t) => (
                <li key={t.key}>
                  <button
                    type="button"
                    onClick={() => select(t.key)}
                    title={t.description}
                    aria-current={t.key === active.key ? "page" : undefined}
                    className={`w-full rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
                      t.key === active.key
                        ? "bg-zinc-900 font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
                        : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                    }`}
                  >
                    {t.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="min-w-0 flex-1">
        <SetupChecklist refreshKey={active.key} />
        <div className="mb-4">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{active.label}</h2>
          <p className="text-xs text-zinc-500">{active.description}</p>
        </div>
        <div key={active.key} className="animate-fade-in-up">
          <ActiveTab />
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4">
        <PageHeader title="Einstellungen" />
        <Suspense fallback={<p className="text-sm text-zinc-500">Lade...</p>}>
          <SettingsContent />
        </Suspense>
      </div>
    </AppShell>
  );
}
