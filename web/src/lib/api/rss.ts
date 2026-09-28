import { apiFetch } from "../api-client";
import type { RssFeed, RssItem } from "../types";

export async function listFeeds(): Promise<RssFeed[]> {
  const data = await apiFetch<{ feeds: RssFeed[] }>("/rss/feeds");
  return data.feeds;
}

export function createFeed(url: string, name?: string): Promise<RssFeed> {
  return apiFetch<RssFeed>("/rss/feeds", { method: "POST", body: { url, name: name || undefined } });
}

export function deleteFeed(feedId: string): Promise<void> {
  return apiFetch<void>(`/rss/feeds/${feedId}`, { method: "DELETE" });
}

export async function listItems(feedId?: string): Promise<RssItem[]> {
  const query = feedId ? `?feed_id=${encodeURIComponent(feedId)}` : "";
  const data = await apiFetch<{ items: RssItem[] }>(`/rss/items${query}`);
  return data.items;
}
