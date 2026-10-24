import { apiFetch } from "../api-client";

export type SearchResultType = "conversation" | "memory" | "contact" | "list_item" | "reminder" | "expense";

export interface SearchResult {
  type: SearchResultType;
  id: string;
  title: string;
  snippet: string | null;
  href: string;
  date: string | null;
}

export async function searchAll(q: string, signal?: AbortSignal): Promise<SearchResult[]> {
  const data = await apiFetch<{ results: SearchResult[] }>(`/search/all?q=${encodeURIComponent(q)}`, { signal });
  return data.results;
}
