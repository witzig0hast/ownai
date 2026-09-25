"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as chatApi from "@/lib/api/chat";
import type { Conversation, Message } from "@/lib/types";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ConversationSidebar({
  conversations,
  selectedId,
  onSelect,
  onCreate,
  creating,
  loading,
}: {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  creating: boolean;
  loading: boolean;
}) {
  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center justify-between border-b border-zinc-200 p-3 dark:border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Conversations</h2>
        <button
          type="button"
          onClick={onCreate}
          disabled={creating}
          className="rounded-md bg-zinc-900 px-2 py-1 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {creating ? "Creating..." : "+ New chat"}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <p className="p-3 text-sm text-zinc-500">Loading...</p>
        ) : conversations.length === 0 ? (
          <p className="p-3 text-sm text-zinc-500">No conversations yet. Start one above.</p>
        ) : (
          <ul>
            {conversations.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={`block w-full truncate px-3 py-2.5 text-left text-sm transition-colors ${
                    c.id === selectedId
                      ? "bg-zinc-100 font-medium text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                      : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-900"
                  }`}
                >
                  <span className="block truncate">{c.title || "Untitled conversation"}</span>
                  <span className="block truncate text-xs text-zinc-400">
                    {formatTime(c.updated_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
            : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
        }`}
      >
        {message.content}
        {message.tool_calls && message.tool_calls.length > 0 ? (
          <div className="mt-2 space-y-1 border-t border-black/10 pt-2 text-xs opacity-70 dark:border-white/10">
            {message.tool_calls.map((tc, i) => (
              <div key={i}>tool: {tc.tool}</div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [creatingConversation, setCreatingConversation] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");

  const [listError, setListError] = useState<string | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      setConversationsLoading(true);
      try {
        const list = await chatApi.listConversations();
        if (cancelled) return;
        setConversations(list);
        if (list.length > 0) {
          setSelectedId((current) => current ?? list[0].id);
        }
      } catch (err) {
        if (cancelled) return;
        setListError(err instanceof ApiError ? err.message : "Failed to load conversations.");
      } finally {
        if (!cancelled) setConversationsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (!selectedId) {
        setMessages([]);
        return;
      }
      setMessagesLoading(true);
      setMessagesError(null);
      try {
        const list = await chatApi.listMessages(selectedId);
        if (!cancelled) setMessages(list);
      } catch (err) {
        if (!cancelled) {
          setMessagesError(err instanceof ApiError ? err.message : "Failed to load messages.");
        }
      } finally {
        if (!cancelled) setMessagesLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleCreateConversation = useCallback(async () => {
    setListError(null);
    setCreatingConversation(true);
    try {
      const conversation = await chatApi.createConversation(null);
      setConversations((prev) => [conversation, ...prev]);
      setSelectedId(conversation.id);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Failed to create conversation.");
    } finally {
      setCreatingConversation(false);
    }
  }, []);

  const handleSend = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const content = input.trim();
      if (!content || !selectedId || sending) return;

      setSendError(null);
      const optimisticMessage: Message = {
        id: `local-${Date.now()}`,
        role: "user",
        content,
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticMessage]);
      setInput("");
      setSending(true);
      try {
        const assistantMessage = await chatApi.sendMessage(selectedId, content);
        setMessages((prev) => [...prev, assistantMessage]);
        setConversations((prev) =>
          prev
            .map((c) =>
              c.id === selectedId ? { ...c, updated_at: assistantMessage.created_at } : c,
            )
            .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1)),
        );
      } catch (err) {
        setSendError(err instanceof ApiError ? err.message : "Failed to send message.");
      } finally {
        setSending(false);
      }
    },
    [input, selectedId, sending],
  );

  return (
    <AppShell>
      <div className="flex flex-1 overflow-hidden">
        <ConversationSidebar
          conversations={conversations}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onCreate={handleCreateConversation}
          creating={creatingConversation}
          loading={conversationsLoading}
        />
        <section className="flex flex-1 flex-col overflow-hidden">
          {listError ? (
            <div className="p-3">
              <ErrorMessage message={listError} />
            </div>
          ) : null}

          {!selectedId ? (
            <div className="flex flex-1 items-center justify-center p-8 text-sm text-zinc-500">
              {conversationsLoading ? "Loading..." : "Select or start a conversation to begin."}
            </div>
          ) : (
            <>
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {messagesLoading ? (
                  <p className="text-sm text-zinc-500">Loading messages...</p>
                ) : (
                  <ErrorMessage message={messagesError} />
                )}
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
                {sending ? (
                  <div className="flex justify-start">
                    <div className="max-w-[75%] rounded-lg bg-zinc-100 px-3 py-2 text-sm text-zinc-500 dark:bg-zinc-800">
                      Thinking...
                    </div>
                  </div>
                ) : null}
                <div ref={bottomRef} />
              </div>
              <form
                onSubmit={handleSend}
                className="flex items-end gap-2 border-t border-zinc-200 p-3 dark:border-zinc-800"
              >
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend(e);
                    }
                  }}
                  placeholder="Message OwnAI..."
                  rows={2}
                  disabled={sending}
                  className="flex-1 resize-none rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-500 focus:outline-none disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900"
                />
                <button
                  type="submit"
                  disabled={sending || !input.trim()}
                  className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {sending ? "Sending..." : "Send"}
                </button>
              </form>
              {sendError ? (
                <div className="px-3 pb-3">
                  <ErrorMessage message={sendError} />
                </div>
              ) : null}
            </>
          )}
        </section>
      </div>
    </AppShell>
  );
}
