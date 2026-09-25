import { apiFetch } from "../api-client";
import type { Suggestion, SuggestionStatus } from "../types";

export async function listSuggestions(status: SuggestionStatus = "open"): Promise<Suggestion[]> {
  const params = new URLSearchParams({ status });
  const data = await apiFetch<{ suggestions: Suggestion[] }>(
    `/notifications/suggestions?${params.toString()}`,
  );
  return data.suggestions;
}

export function applySuggestion(id: string): Promise<Suggestion> {
  return apiFetch<Suggestion>(`/notifications/suggestions/${id}/apply`, {
    method: "POST",
  });
}

export function dismissSuggestion(id: string): Promise<{ status: "dismissed" }> {
  return apiFetch<{ status: "dismissed" }>(`/notifications/suggestions/${id}/dismiss`, {
    method: "POST",
  });
}
