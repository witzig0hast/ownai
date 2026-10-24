"use client";

import { useState } from "react";
import type { Expense } from "@/lib/types";

type Range = "weeks" | "months";

interface Bucket {
  key: string;
  label: string;
  start: Date;
  end: Date; // exclusive
  total: number;
  current: boolean;
}

function parseDay(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

function startOfWeek(d: Date): Date {
  const day = (d.getDay() + 6) % 7; // Monday = 0
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() - day);
}

function buildBuckets(expenses: Expense[], range: Range, now: Date): Bucket[] {
  const buckets: Bucket[] = [];
  if (range === "weeks") {
    const thisWeek = startOfWeek(now);
    for (let i = 7; i >= 0; i--) {
      const start = new Date(thisWeek.getFullYear(), thisWeek.getMonth(), thisWeek.getDate() - i * 7);
      const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 7);
      buckets.push({
        key: start.toISOString(),
        label: start.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" }),
        start,
        end,
        total: 0,
        current: i === 0,
      });
    }
  } else {
    for (let i = 5; i >= 0; i--) {
      const start = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const end = new Date(start.getFullYear(), start.getMonth() + 1, 1);
      buckets.push({
        key: start.toISOString(),
        label: start.toLocaleDateString("de-DE", { month: "short" }),
        start,
        end,
        total: 0,
        current: i === 0,
      });
    }
  }
  for (const e of expenses) {
    const day = parseDay(e.spent_at);
    const bucket = buckets.find((b) => day >= b.start && day < b.end);
    if (bucket) bucket.total += e.amount;
  }
  return buckets;
}

function euro(n: number, digits = 2): string {
  return n.toLocaleString("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: digits, minimumFractionDigits: digits });
}

/** Spending over time (last 8 weeks or 6 months) plus the category split for that range. */
export function ExpensesChart({ expenses }: { expenses: Expense[] }) {
  const [range, setRange] = useState<Range>("weeks");
  const buckets = buildBuckets(expenses, range, new Date());
  const max = Math.max(...buckets.map((b) => b.total), 1);
  const rangeTotal = buckets.reduce((sum, b) => sum + b.total, 0);
  const average = rangeTotal / buckets.length;

  const rangeStart = buckets[0].start;
  const byCategory = new Map<string, number>();
  for (const e of expenses) {
    if (parseDay(e.spent_at) < rangeStart) continue;
    const cat = e.category || "Ohne Kategorie";
    byCategory.set(cat, (byCategory.get(cat) ?? 0) + e.amount);
  }
  const categories = [...byCategory.entries()].sort((a, b) => b[1] - a[1]);

  const summary = buckets.map((b) => `${b.label}: ${euro(b.total)}`).join(", ");

  return (
    <div className="animate-fade-in-up mb-3 rounded-2xl border border-zinc-200 p-4 shadow-sm dark:border-zinc-800">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {range === "weeks" ? "Letzte 8 Wochen" : "Letzte 6 Monate"}: {euro(rangeTotal)}
          </p>
          <p className="text-xs text-zinc-500">
            Ø {euro(average)} pro {range === "weeks" ? "Woche" : "Monat"}
          </p>
        </div>
        <div className="flex gap-1 rounded-full bg-zinc-100 p-1 text-xs dark:bg-zinc-900" role="radiogroup" aria-label="Zeitraum">
          {(["weeks", "months"] as Range[]).map((r) => (
            <button
              key={r}
              type="button"
              role="radio"
              aria-checked={range === r}
              onClick={() => setRange(r)}
              className={`rounded-full px-2.5 py-1 font-medium transition-all ${
                range === r ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-100" : "text-zinc-500"
              }`}
            >
              {r === "weeks" ? "Wochen" : "Monate"}
            </button>
          ))}
        </div>
      </div>

      <div role="img" aria-label={`Ausgaben je ${range === "weeks" ? "Woche" : "Monat"}: ${summary}`}>
        <div className="flex h-36 items-end gap-1.5" aria-hidden>
          {buckets.map((b) => (
            <div key={b.key} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1" title={`${b.label}: ${euro(b.total)}`}>
              <span className="text-[10px] text-zinc-500 tabular-nums">{b.total > 0 ? euro(b.total, 0) : ""}</span>
              <div
                className={`w-full max-w-10 rounded-t-md ${b.current ? "bg-indigo-500" : "bg-indigo-200 dark:bg-indigo-900"}`}
                style={{ height: `${Math.max((b.total / max) * 100, b.total > 0 ? 3 : 0)}%` }}
              />
            </div>
          ))}
        </div>
        <div className="mt-1 flex gap-1.5 border-t border-zinc-200 pt-1 dark:border-zinc-800" aria-hidden>
          {buckets.map((b) => (
            <span
              key={b.key}
              className={`min-w-0 flex-1 truncate text-center text-[10px] ${b.current ? "font-semibold text-zinc-900 dark:text-zinc-100" : "text-zinc-500"}`}
            >
              {b.label}
            </span>
          ))}
        </div>
      </div>

      {categories.length > 0 ? (
        <ul className="mt-4 flex flex-col gap-1.5">
          {categories.map(([cat, sum]) => (
            <li key={cat} className="text-xs">
              <div className="mb-0.5 flex justify-between">
                <span className="text-zinc-700 dark:text-zinc-300">{cat}</span>
                <span className="text-zinc-500 tabular-nums">
                  {euro(sum)} · {Math.round((sum / rangeTotal) * 100)}%
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(sum / rangeTotal) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
