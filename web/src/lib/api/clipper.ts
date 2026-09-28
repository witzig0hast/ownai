import { apiFetch } from "../api-client";
import type { ClippedPage } from "../types";

export function clipUrl(url: string): Promise<ClippedPage> {
  return apiFetch<ClippedPage>("/clip", { method: "POST", body: { url } });
}
