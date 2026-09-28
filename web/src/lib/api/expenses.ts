import { apiFetch } from "../api-client";
import type { Expense, ExpensesList } from "../types";

export function listExpenses(): Promise<ExpensesList> {
  return apiFetch<ExpensesList>("/expenses");
}

export function createExpense(payload: {
  amount: number;
  description: string;
  category?: string | null;
}): Promise<Expense> {
  return apiFetch<Expense>("/expenses", { method: "POST", body: payload });
}

export function deleteExpense(expenseId: string): Promise<void> {
  return apiFetch<void>(`/expenses/${expenseId}`, { method: "DELETE" });
}
