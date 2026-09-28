import { apiFetch } from "../api-client";
import type { ListKind, TodoList } from "../types";

export async function listLists(): Promise<TodoList[]> {
  const data = await apiFetch<{ lists: TodoList[] }>("/lists");
  return data.lists;
}

export function createList(name: string, kind: ListKind): Promise<TodoList> {
  return apiFetch<TodoList>("/lists", { method: "POST", body: { name, kind } });
}

export function renameList(listId: string, name: string): Promise<TodoList> {
  return apiFetch<TodoList>(`/lists/${listId}`, { method: "PATCH", body: { name } });
}

export function deleteList(listId: string): Promise<void> {
  return apiFetch<void>(`/lists/${listId}`, { method: "DELETE" });
}

export function addItem(listId: string, content: string): Promise<TodoList> {
  return apiFetch<TodoList>(`/lists/${listId}/items`, { method: "POST", body: { content } });
}

export function updateItem(
  listId: string,
  itemId: string,
  patch: { content?: string; done?: boolean },
): Promise<TodoList> {
  return apiFetch<TodoList>(`/lists/${listId}/items/${itemId}`, { method: "PATCH", body: patch });
}

export function deleteItem(listId: string, itemId: string): Promise<TodoList> {
  return apiFetch<TodoList>(`/lists/${listId}/items/${itemId}`, { method: "DELETE" });
}
