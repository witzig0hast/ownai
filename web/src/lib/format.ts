// Shared, German, human-friendly date formatting. The browser's default toLocaleString() gave
// "24.10.2026, 09:45:11" everywhere - seconds nobody needs, and no "heute"/"gestern".

const DAY_MS = 24 * 60 * 60 * 1000;

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function time(d: Date): string {
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

function parse(iso: string): Date | null {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "heute, 09:45" / "gestern, 18:02" / "morgen, 08:00" / "Mo., 09:45" (within a week either
 * way) / "24.10.2026, 09:45". Falls back to the raw input for anything unparseable. */
export function formatDateTime(iso: string, now: Date = new Date()): string {
  const d = parse(iso);
  if (!d) return iso;
  const dayDiff = Math.round((startOfDay(d) - startOfDay(now)) / DAY_MS);
  if (dayDiff === 0) return `heute, ${time(d)}`;
  if (dayDiff === -1) return `gestern, ${time(d)}`;
  if (dayDiff === 1) return `morgen, ${time(d)}`;
  if (Math.abs(dayDiff) < 7) return `${d.toLocaleDateString("de-DE", { weekday: "short" })}, ${time(d)}`;
  return `${d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })}, ${time(d)}`;
}

/** "24.10.2026" (or "heute"/"gestern"). */
export function formatDate(iso: string, now: Date = new Date()): string {
  const d = parse(iso);
  if (!d) return iso;
  const dayDiff = Math.round((startOfDay(d) - startOfDay(now)) / DAY_MS);
  if (dayDiff === 0) return "heute";
  if (dayDiff === -1) return "gestern";
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Bucket for grouping lists by recency (chat sidebar). */
export function recencyGroup(iso: string, now: Date = new Date()): "Heute" | "Gestern" | "Diese Woche" | "Älter" {
  const d = parse(iso);
  if (!d) return "Älter";
  const dayDiff = Math.round((startOfDay(now) - startOfDay(d)) / DAY_MS);
  if (dayDiff <= 0) return "Heute";
  if (dayDiff === 1) return "Gestern";
  if (dayDiff < 7) return "Diese Woche";
  return "Älter";
}
