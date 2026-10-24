"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import * as onboardingApi from "@/lib/api/onboarding";
import { useAuth } from "@/lib/auth-context";

function Section({ title, children, defaultOpen = false }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  return (
    <details
      open={defaultOpen}
      className="group rounded-2xl border border-zinc-200 p-4 shadow-sm open:pb-5 dark:border-zinc-800"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        {title}
        <span className="text-zinc-400 transition-transform group-open:rotate-90" aria-hidden>
          ›
        </span>
      </summary>
      <div className="mt-3 flex flex-col gap-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">{children}</div>
    </details>
  );
}

function TabLink({ tab, children }: { tab: string; children: ReactNode }) {
  return (
    <Link href={`/settings?tab=${tab}`} className="font-medium text-zinc-900 underline dark:text-zinc-100">
      {children}
    </Link>
  );
}

function Example({ children }: { children: ReactNode }) {
  return <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">„{children}“</span>;
}

function RestoreChecklistButton() {
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");

  async function restore() {
    setState("busy");
    try {
      await onboardingApi.setSetupDismissed(false);
      setState("done");
    } catch {
      setState("error");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={restore}
        disabled={state === "busy"}
        className="rounded-full border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300"
      >
        Einrichtungs-Checkliste wieder anzeigen
      </button>
      {state === "done" ? <span className="text-xs text-emerald-600">Erscheint wieder auf „Sprechen“ und in den Einstellungen.</span> : null}
      {state === "error" ? <span className="text-xs text-red-600">Hat nicht geklappt, bitte erneut versuchen.</span> : null}
    </div>
  );
}

export default function HelpPage() {
  const { user } = useAuth();

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-2xl">
          <PageHeader title="Hilfe" />
          <p className="mb-5 text-sm text-zinc-500">
            Was OwnAI kann, wie die einzelnen Bereiche zusammenhängen und was du tun kannst, wenn etwas
            nicht klappt.
          </p>

          <div className="flex flex-col gap-3">
            <Section title="Erste Schritte" defaultOpen>
              <p>
                OwnAI ist nur so nützlich wie das, was du verbindest. Die <strong>Einrichtungs-Checkliste</strong>{" "}
                (auf der Übersicht und in den Einstellungen) zeigt, was noch fehlt - Kalender, E-Mail, Home
                Assistant, Web-Suche.
              </p>
              <p>
                Am Handy erreichst du alles über die Leiste unten: <strong>Übersicht</strong>,{" "}
                <strong>Sprechen</strong>, <strong>Chat</strong> und unter <strong>Mehr</strong> Einstellungen,
                Hilfe und Abmelden. Oben rechts ist die Suche.
              </p>
              <p>
                <strong>Als App installieren:</strong> Am iPad/iPhone in Safari „Teilen → Zum Home-Bildschirm“, am
                PC in Chrome/Edge das Installieren-Symbol in der Adressleiste. Dann läuft OwnAI im eigenen Fenster
                und kann (auf iOS nur so) Push-Benachrichtigungen empfangen.
              </p>
              <RestoreChecklistButton />
            </Section>

            <Section title="Übersicht und Morgen-Briefing">
              <p>
                Die <strong>Übersicht</strong> ist deine Startseite: Termine heute, Wetter, offene Listen (direkt
                abhaken oder ergänzen), die nächsten Erinnerungen, Geburtstage und was du diesen Monat ausgegeben
                hast. Jede Karte führt zur vollständigen Ansicht.
              </p>
              <p>
                „Tagesbriefing vorlesen“ fasst das alles in ein paar Sätzen zusammen. Unter{" "}
                <TabLink tab="account">Konto</TabLink> kannst du dir das Briefing jeden Morgen zu einer festen
                Uhrzeit als Push schicken lassen und deinen Wohnort fürs Wetter eintragen.
              </p>
            </Section>

            <Section title="Sprechen oder schreiben">
              <p>
                <strong>Sprechen</strong> ist ein Live-Gespräch: Mikrofon antippen, reden, die Antwort wird
                vorgelesen. Das Mikrofon kannst du zwischendurch stummschalten. Funktioniert nur über https (oder
                localhost), sonst blockiert der Browser das Mikrofon - die antippbaren Vorschläge darunter gehen
                aber immer.
              </p>
              <p>
                <strong>Chat</strong> ist das Gleiche als Text, mit Verlauf, Bild-Upload (Text erkennen/Bild
                beschreiben) und Spracheingabe per Knopf. Unterhaltungen lassen sich archivieren oder löschen.
              </p>
              <p>
                Pro Unterhaltung wählst du über dem Eingabefeld einen <strong>Modus</strong>: <em>Allgemein</em> (alle Werkzeuge),{" "}
                <em>Zuhause</em> (Fokus Smart Home &amp; Timer) oder <em>Organisation</em> (Kalender, Dateien,
                E-Mail).
              </p>
            </Section>

            <Section title="Was du fragen kannst">
              <ul className="ml-4 list-disc space-y-1">
                <li>Kalender: <Example>Was steht morgen an?</Example> <Example>Trag Freitag 18 Uhr Kino ein</Example></li>
                <li>Smart Home: <Example>Mach das Licht im Wohnzimmer aus</Example></li>
                <li>Timer: <Example>Timer 12 Minuten für die Nudeln</Example></li>
                <li>Erinnerungen: <Example>Erinnere mich jeden Montag um 8 an den Müll</Example></li>
                <li>Listen: <Example>Setz Milch auf die Einkaufsliste</Example></li>
                <li>Ausgaben: <Example>Ich hab 23 Euro für Tanken ausgegeben</Example></li>
                <li>Kontakte: <Example>Lisa hat am 4. März Geburtstag</Example></li>
                <li>Wetter &amp; Web: <Example>Wie wird das Wetter in Hamburg?</Example> <Example>Such nach ...</Example></li>
                <li>E-Mail: <Example>Schick Tom eine Mail, dass ich später komme</Example></li>
                <li>Dateien: <Example>Schreib mir eine Packliste als Datei</Example></li>
              </ul>
              <p>Alles davon kannst du auch direkt über die Übersicht ansehen und bearbeiten.</p>
            </Section>

            <Section title="Suchen und Teilen">
              <p>
                Die <strong>Suche</strong> (Lupe oben) findet Unterhaltungen, Gespeichertes aus dem Gedächtnis,
                Kontakte, Listeneinträge, Erinnerungen und Ausgaben auf einmal.
              </p>
              <p>
                <strong>Teilen an OwnAI:</strong> Ist OwnAI als App installiert, taucht es auf Android und in
                Chrome/Edge am PC im „Teilen“-Menü anderer Apps auf. Links kannst du dann zusammenfassen lassen,
                Fotos von Kassenbons direkt als Ausgabe erfassen. iPhone und iPad bieten das für Web-Apps leider
                nicht an.
              </p>
              <p>
                <strong>Dunkelmodus:</strong> unter <TabLink tab="account">Konto → Darstellung</TabLink>, pro
                Gerät.
              </p>
            </Section>

            <Section title="Gedächtnis">
              <p>
                Sag <Example>Merk dir, dass ich vegetarisch esse</Example> - der Assistent speichert das dauerhaft und
                berücksichtigt es in jeder künftigen Unterhaltung. Unter <TabLink tab="memory">Gedächtnis</TabLink>{" "}
                siehst du alles Gespeicherte und kannst Einträge löschen.
              </p>
            </Section>

            <Section title="Erinnerungen, Timer und Push">
              <p>
                Timer und Erinnerungen melden sich per Push-Benachrichtigung - aktiviere sie einmal pro Gerät unter{" "}
                <TabLink tab="account">Konto</TabLink>. Ohne Push klingeln Timer nur, solange OwnAI geöffnet ist.
              </p>
            </Section>

            <Section title="Automatisierungen und Agenten">
              <p>
                <strong>Automatisierungen</strong> (<TabLink tab="automations">hier</TabLink>) sind Wenn-Dann-Regeln
                auf Basis von Home Assistant, z.B. „Wenn die Waschmaschine fertig ist, schick mir eine Nachricht“.
              </p>
              <p>
                <strong>Agenten</strong> (<TabLink tab="permanent-agents">hier</TabLink>) erledigen regelmäßig und
                selbstständig eine Aufgabe, z.B. jeden Morgen die News zusammenfassen. Ihre Ergebnisse findest du
                dort - oder du fragst <Example>Was haben meine Agenten gefunden?</Example>
              </p>
            </Section>

            <Section title="Eingehende E-Mails und Bestätigungen">
              <p>
                Wenn du unter <TabLink tab="email">E-Mail</TabLink> ein IMAP-Postfach hinterlegst und die Funktion
                einschaltest, liest der Assistent neue Mails und reagiert darauf.
              </p>
              <p>
                Alles mit Folgen (Mail senden, Termin eintragen, etwas löschen, ...) führt er dabei <strong>nicht
                selbst aus</strong>, sondern fragt dich: oben erscheint dann ein Fenster „Bestätigung ausstehend“, in
                dem du jede Aktion annehmen oder ablehnen kannst. Nur Lesendes (Kalender ansehen, Wetter, ...) läuft
                ohne Rückfrage.
              </p>
            </Section>

            <Section title="Web-Clipper, News und Agent Bus">
              <p>
                <strong>Web-Clipper</strong> (<TabLink tab="clipper">hier</TabLink>): ein Lesezeichen, das die gerade
                offene Webseite an den Assistenten schickt - zum Zusammenfassen oder Merken.
              </p>
              <p>
                <strong>News</strong> (<TabLink tab="rss">hier</TabLink>): RSS-Feeds, die er für dich liest und
                zusammenfasst.
              </p>
              <p>
                <strong>Agent Bus</strong> (<TabLink tab="agent-bus">hier</TabLink>): für Fortgeschrittene - andere
                Programme oder KI-Agenten bekommen einen eigenen Schlüssel und können mit deinem Assistenten
                Nachrichten austauschen.
              </p>
            </Section>

            <Section title="Vorschläge (Android)">
              <p>
                Mit der Android-App kann OwnAI deine Benachrichtigungen (z.B. SMS, Messenger) lesen und daraus
                Vorschläge machen - etwa einen Termin, der in einer Nachricht erwähnt wurde. Der Menüpunkt
                „Vorschläge“ erscheint erst, wenn ein Android-Gerät verbunden ist.
              </p>
            </Section>

            <Section title="Konto und Sicherheit">
              <p>
                Ist auf dem Server Single Sign-On eingerichtet, kannst du dein Konto unter{" "}
                <TabLink tab="account">Konto</TabLink> mit deinem Identity Provider verknüpfen und dich danach auch
                darüber anmelden. Der Passwort-Login bleibt immer zusätzlich bestehen.
              </p>
              <p>
                Nach mehreren falschen Passwörtern hintereinander wird der Login für dieses Konto für einige Minuten
                gesperrt - das schützt vor automatisiertem Raten. Einfach kurz warten.
              </p>
            </Section>

            <Section title="Wenn etwas nicht klappt">
              <ul className="ml-4 list-disc space-y-1">
                <li>
                  <strong>Antwortet nicht / dauert ewig:</strong> Das Sprachmodell läuft auf deinem eigenen Server und
                  braucht beim ersten Mal nach einem Neustart etwas, um zu laden.
                </li>
                <li>
                  <strong>Eine Integration geht nicht:</strong> Unter <TabLink tab="logs">Logs</TabLink> steht, was im
                  Hintergrund passiert ist, inklusive Fehlermeldung (z.B. beim Mailversand).
                </li>
                {user?.is_admin ? (
                  <li>
                    <strong>Als Admin:</strong> Unter <Link href="/admin" className="font-medium text-zinc-900 underline dark:text-zinc-100">Admin → Systemstatus</Link>{" "}
                    siehst du live, ob Datenbank, Sprachmodell, Spracherkennung usw. erreichbar sind - inklusive
                    Hinweis, welches Modell fehlt. Backups: <code>scripts/backup.sh</code> auf dem Server (siehe README).
                  </li>
                ) : null}
              </ul>
            </Section>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
