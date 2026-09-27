import { apiFetch } from "../api-client";
import type { Conversation, Message, Skill } from "../types";

export async function listConversations(includeArchived = false): Promise<Conversation[]> {
  const query = includeArchived ? "?include_archived=true" : "";
  const data = await apiFetch<{ conversations: Conversation[] }>(`/chat/conversations${query}`);
  return data.conversations;
}

export function createConversation(title: string | null): Promise<Conversation> {
  return apiFetch<Conversation>("/chat/conversations", {
    method: "POST",
    body: { title },
  });
}

export function updateConversation(
  conversationId: string,
  patch: { title?: string; archived?: boolean; skill?: string },
): Promise<Conversation> {
  return apiFetch<Conversation>(`/chat/conversations/${conversationId}`, {
    method: "PATCH",
    body: patch,
  });
}

export async function listSkills(): Promise<Skill[]> {
  const data = await apiFetch<{ skills: Skill[] }>("/chat/skills");
  return data.skills;
}

export function deleteConversation(conversationId: string): Promise<void> {
  return apiFetch<void>(`/chat/conversations/${conversationId}`, { method: "DELETE" });
}

/** Best-effort: fire-and-forget from the caller's side too (errors here shouldn't block the UI). */
export function warmup(): Promise<void> {
  return apiFetch<void>("/chat/warmup", { method: "POST" });
}

export async function listMessages(conversationId: string): Promise<Message[]> {
  const data = await apiFetch<{ messages: Message[] }>(
    `/chat/conversations/${conversationId}/messages`,
  );
  return data.messages;
}

export async function sendMessage(conversationId: string, content: string): Promise<Message> {
  const data = await apiFetch<{ message: Message }>(
    `/chat/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: { content },
    },
  );
  return data.message;
}
