"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as calendarApi from "@/lib/api/calendar";
import type { CalendarEvent } from "@/lib/types";

const CALENDAR_ENABLED_STORAGE_KEY = "ownai.calendarEnabled";

function toDateInputValue(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function dateInputToIsoRangeStart(value: string): string {
  return new Date(`${value}T00:00:00`).toISOString();
}

function dateInputToIsoRangeEnd(value: string): string {
  return new Date(`${value}T23:59:59`).toISOString();
}

function formatEventTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function defaultRange(): { start: string; end: string } {
  const today = new Date();
  const end = new Date();
  end.setDate(end.getDate() + 30);
  return { start: toDateInputValue(today), end: toDateInputValue(end) };
}

function readEnabledPreference(): boolean {
  if (typeof window === "undefined") return true;
  try {
    const stored = window.localStorage.getItem(CALENDAR_ENABLED_STORAGE_KEY);
    return stored === null ? true : stored === "true";
  } catch {
    return true;
  }
}

export function CalendarTab() {
  // Per-viewer preference, not shared state - same pattern as Chat's "auto-read replies"
  // toggle (localStorage, read once via a lazy initializer).
  const [enabled, setEnabled] = useState(readEnabledPreference);

  function toggleEnabled() {
    setEnabled((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(CALENDAR_ENABLED_STORAGE_KEY, String(next));
      } catch {
        // best-effort only
      }
      return next;
    });
  }

  const initialRange = defaultRange();
  const [rangeStart, setRangeStart] = useState(initialRange.start);
  const [rangeEnd, setRangeEnd] = useState(initialRange.end);

  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [notConnected, setNotConnected] = useState(false);

  const loadEvents = useCallback((start: string, end: string) => {
    setEventsLoading(true);
    setEventsError(null);
    setNotConnected(false);
    calendarApi
      .listEvents(dateInputToIsoRangeStart(start), dateInputToIsoRangeEnd(end))
      .then((list) => {
        setEvents([...list].sort((a, b) => (a.start < b.start ? -1 : 1)));
      })
      .catch((err) => {
        if (err instanceof ApiError && err.code === "calendar_not_connected") {
          setNotConnected(true);
        } else {
          setEventsError(err instanceof ApiError ? err.message : "Failed to load events.");
        }
      })
      .finally(() => setEventsLoading(false));
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void (async () => {
      loadEvents(initialRange.start, initialRange.end);
    })();
    // Only run once on mount (and when re-enabled); the "Apply" button re-triggers explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  // --- Create event form ---
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [location, setLocation] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  async function handleCreateEvent(e: FormEvent) {
    e.preventDefault();
    setCreateError(null);
    if (!title || !start || !end) {
      setCreateError("Title, start and end are required.");
      return;
    }
    setCreating(true);
    try {
      const created = await calendarApi.createEvent({
        title,
        start: new Date(start).toISOString(),
        end: new Date(end).toISOString(),
        location: location || null,
      });
      setEvents((prev) => [...prev, created].sort((a, b) => (a.start < b.start ? -1 : 1)));
      setTitle("");
      setStart("");
      setEnd("");
      setLocation("");
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Failed to create event.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <label className="mb-4 flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
        <input type="checkbox" checked={enabled} onChange={toggleEnabled} className="h-4 w-4" />
        Kalender aktivieren
      </label>

      {!enabled ? (
        <p className="text-sm text-zinc-500">
          Kalender ist deaktiviert. Deine CalDAV-Verbindung (falls vorhanden) bleibt bestehen, die
          Termin-Ansicht ist nur ausgeblendet.
        </p>
      ) : (
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <section className="flex-1 rounded-lg border border-zinc-200 dark:border-zinc-800">
            <div className="flex flex-wrap items-end gap-3 border-b border-zinc-200 p-3 dark:border-zinc-800">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-zinc-700 dark:text-zinc-300">From</span>
                <input
                  type="date"
                  value={rangeStart}
                  onChange={(e) => setRangeStart(e.target.value)}
                  className="rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-zinc-700 dark:text-zinc-300">To</span>
                <input
                  type="date"
                  value={rangeEnd}
                  onChange={(e) => setRangeEnd(e.target.value)}
                  className="rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>
              <button
                type="button"
                onClick={() => loadEvents(rangeStart, rangeEnd)}
                className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900"
              >
                Apply
              </button>
            </div>
            <div className="p-3">
              <h2 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                Upcoming events
              </h2>
              <ErrorMessage message={eventsError} />
              {notConnected ? (
                <p className="text-sm text-zinc-500">
                  Kein Kalender verbunden. Verbinde ihn oben im Tab &quot;Integrations&quot;.
                </p>
              ) : eventsLoading ? (
                <p className="text-sm text-zinc-500">Loading...</p>
              ) : events.length === 0 ? (
                <p className="text-sm text-zinc-500">No events in this range.</p>
              ) : (
                <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
                  {events.map((event) => (
                    <li key={event.id} className="py-2">
                      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                        {event.title}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {formatEventTime(event.start)} — {formatEventTime(event.end)}
                        {event.location ? ` · ${event.location}` : ""}
                      </p>
                      <p className="text-xs uppercase tracking-wide text-zinc-400">{event.source}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="flex w-full flex-col gap-6 lg:w-80">
            <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
              <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                New event
              </h2>
              <form onSubmit={handleCreateEvent} className="flex flex-col gap-3">
                <input
                  type="text"
                  required
                  placeholder="Title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
                <label className="flex flex-col gap-1 text-xs text-zinc-500">
                  Start
                  <input
                    type="datetime-local"
                    required
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                    className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                  />
                </label>
                <label className="flex flex-col gap-1 text-xs text-zinc-500">
                  End
                  <input
                    type="datetime-local"
                    required
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                    className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                  />
                </label>
                <input
                  type="text"
                  placeholder="Location (optional)"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
                <ErrorMessage message={createError} />
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {creating ? "Creating..." : "Create event"}
                </button>
              </form>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
