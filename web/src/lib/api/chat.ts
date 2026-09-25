import { apiFetch } from "../api-client";
import type { Conversation, Message } from "../types";

export async function listConversations(): Promise<Conversation[]> {
  const data = await apiFetch<{ conversations: Conversation[] }>("/chat/conversations");
  return data.conversations;
}

export function createConversation(title: string | null): Promise<Conversation> {
  return apiFetch<Conversation>("/chat/conversations", {
    method: "POST",
    body: { title },
  });
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
