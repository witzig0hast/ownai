"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as remindersApi from "@/lib/api/reminders";
import type { Reminder, ReminderRecurrence, Weekday } from "@/lib/types";

const WEEKDAY_LABELS: Record<Weekday, string> = {
  mon: "Montag", tue: "Dienstag", wed: "Mittwoch", thu: "Donnerstag",
  fri: "Freitag", sat: "Samstag", sun: "Sonntag",
};

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function describeReminder(r: Reminder): string {
  const time = `${pad2(r.hour)}:${pad2(r.minute)}`;
  if (r.recurrence === "daily") return `Täglich um ${time}`;
  if (r.recurrence === "weekly") return `Jeden ${r.weekday ? WEEKDAY_LABELS[r.weekday] : "?"} um ${time}`;
  return `Monatlich am ${r.day_of_month}. um ${time}`;
}

export function RemindersTab() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [label, setLabel] = useState("");
  const [recurrence, setRecurrence] = useState<ReminderRecurrence>("daily");
  const [time, setTime] = useState("08:00");
  const [weekday, setWeekday] = useState<Weekday>("mon");
  const [dayOfMonth, setDayOfMonth] = useState("1");
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    remindersApi
      .listReminders()
      .then(setReminders)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Laden fehlgeschlagen."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void (async () => {
      load();
    })();
  }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!label.trim()) return;
    setAdding(true);
    setError(null);
    try {
      const [hour, minute] = time.split(":").map(Number);
      await remindersApi.createReminder({
        label: label.trim(),
        recurrence,
        hour,
        minute,
        weekday: recurrence === "weekly" ? weekday : null,
        day_of_month: recurrence === "monthly" ? Number(dayOfMonth) : null,
      });
      setLabel("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleToggleActive(reminder: Reminder) {
    try {
      const updated = await remindersApi.updateReminder(reminder.id, { active: !reminder.active });
      setReminders((prev) => prev.map((r) => (r.id === reminder.id ? updated : r)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ändern fehlgeschlagen.");
    }
  }

  async function handleDelete(id: string) {
    try {
      await remindersApi.deleteReminder(id);
      setReminders((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Wiederkehrende Erinnerungen — im Gegensatz zu einem Timer laufen sie dauerhaft weiter und melden
        sich immer wieder zur eingestellten Uhrzeit per Push.
      </p>

      <form onSubmit={handleAdd} className="mb-4 flex flex-col gap-2 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
        <input
          type="text"
          placeholder="Woran erinnern? z.B. 'Tabletten nehmen'"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={recurrence}
            onChange={(e) => setRecurrence(e.target.value as ReminderRecurrence)}
            className="rounded-md border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          >
            <option value="daily">Täglich</option>
            <option value="weekly">Wöchentlich</option>
            <option value="monthly">Monatlich</option>
          </select>
          {recurrence === "weekly" && (
            <select
              value={weekday}
              onChange={(e) => setWeekday(e.target.value as Weekday)}
              className="rounded-md border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {Object.entries(WEEKDAY_LABELS).map(([key, label2]) => (
                <option key={key} value={key}>{label2}</option>
              ))}
            </select>
          )}
          {recurrence === "monthly" && (
            <input
              type="number"
              min={1}
              max={31}
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(e.target.value)}
              className="w-20 rounded-md border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          )}
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="rounded-md border border-zinc-300 px-2 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <button
          type="submit"
          disabled={adding || !label.trim()}
          className="self-start rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Erinnerung hinzufügen
        </button>
      </form>

      <ErrorMessage message={error} />

      {loading ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : reminders.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch keine Erinnerungen.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {reminders.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
              <div className={r.active ? "" : "opacity-50"}>
                <p className="text-zinc-900 dark:text-zinc-100">{r.label}</p>
                <p className="text-xs text-zinc-400">{describeReminder(r)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <button
                  type="button"
                  onClick={() => handleToggleActive(r)}
                  className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                >
                  {r.active ? "Pausieren" : "Aktivieren"}
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(r.id)}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  Löschen
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
