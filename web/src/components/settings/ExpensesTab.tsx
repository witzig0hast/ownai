"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as expensesApi from "@/lib/api/expenses";
import type { Expense, ExpensesList } from "@/lib/types";

function formatAmount(amount: number): string {
  return amount.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("de-DE");
  } catch {
    return iso;
  }
}

export function ExpensesTab() {
  const [data, setData] = useState<ExpensesList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    expensesApi
      .listExpenses()
      .then(setData)
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
    const parsedAmount = Number(amount.replace(",", "."));
    if (!description.trim() || !parsedAmount || parsedAmount <= 0) return;
    setAdding(true);
    setError(null);
    try {
      await expensesApi.createExpense({
        amount: parsedAmount,
        description: description.trim(),
        category: category.trim() || null,
      });
      setAmount("");
      setDescription("");
      setCategory("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Hinzufügen fehlgeschlagen.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await expensesApi.deleteExpense(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Löschen fehlgeschlagen.");
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Einfacher Ausgaben-Tracker mit Gesamtsumme und Aufschlüsselung nach Kategorie.
      </p>

      <form onSubmit={handleAdd} className="mb-4 flex flex-col gap-2 rounded-2xl border border-zinc-200 p-3 dark:border-zinc-800">
        <div className="flex gap-2">
          <input
            type="text"
            inputMode="decimal"
            placeholder="Betrag, z.B. 12,50"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-32 rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
          />
          <input
            type="text"
            placeholder="Kategorie (optional)"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="flex-1 rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <input
          type="text"
          placeholder="Wofür? z.B. 'Mittagessen'"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="rounded-xl border border-zinc-300 px-3 py-2 text-sm transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={adding || !description.trim() || !amount.trim()}
          className="self-start rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white shadow-sm transition-all hover:scale-[1.03] hover:bg-zinc-700 hover:shadow active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Ausgabe eintragen
        </button>
      </form>

      <ErrorMessage message={error} />

      {loading || !data ? (
        <p className="text-sm text-zinc-500">Lade...</p>
      ) : data.expenses.length === 0 ? (
        <p className="text-sm text-zinc-500">Noch keine Ausgaben.</p>
      ) : (
        <>
          <div className="animate-fade-in-up mb-3 rounded-2xl border border-zinc-200 p-3 text-sm shadow-sm dark:border-zinc-800">
            <p className="mb-1 font-medium text-zinc-900 dark:text-zinc-100">
              Gesamt: {formatAmount(data.total)} €
            </p>
            <ul className="text-xs text-zinc-500">
              {Object.entries(data.by_category).map(([cat, sum]) => (
                <li key={cat}>
                  {cat}: {formatAmount(sum)} €
                </li>
              ))}
            </ul>
          </div>

          <ul className="divide-y divide-zinc-200 rounded-2xl border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
            {data.expenses.map((e: Expense) => (
              <li key={e.id} className="animate-fade-in-up flex items-center justify-between gap-3 px-3 py-2 text-sm transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-900/60">
                <div>
                  <p className="text-zinc-900 dark:text-zinc-100">{e.description}</p>
                  <p className="text-xs text-zinc-400">
                    {formatDate(e.spent_at)}
                    {e.category ? ` · ${e.category}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">{formatAmount(e.amount)} €</span>
                  <button
                    type="button"
                    onClick={() => handleDelete(e.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Löschen
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
