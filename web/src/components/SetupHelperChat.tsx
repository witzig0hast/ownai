"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as chatApi from "@/lib/api/chat";
import type { Message } from "@/lib/types";

const HELPER_CONVERSATION_TITLE = "Integrations-Hilfe";

/**
 * A small embedded chat, scoped to its own dedicated conversation, that answers setup
 * questions right where the user is trying to connect an integration (e.g. "wo finde ich
 * meine CalDAV-URL?", "wie erstelle ich ein Home-Assistant-Long-Lived-Token?"). Reuses the
 * normal chat backend — same OwnAI assistant, just a separate conversation so it doesn't mix
 * with the user's regular chat history.
 */
export function SetupHelperChat() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const conversations = await chatApi.listConversations();
        if (cancelled) return;
        const existing = conversations.find((c) => c.title === HELPER_CONVERSATION_TITLE);
        if (existing) {
          setConversationId(existing.id);
          const list = await chatApi.listMessages(existing.id);
          if (!cancelled) setMessages(list);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Konnte Hilfe-Chat nicht laden.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const content = input.trim();
      if (!content || sending) return;

      setError(null);
      setSending(true);
      setInput("");
      const optimisticMessage: Message = {
        id: `local-${Date.now()}`,
        role: "user",
        content,
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticMessage]);

      try {
        let id = conversationId;
        if (!id) {
          const conversation = await chatApi.createConversation(HELPER_CONVERSATION_TITLE);
          id = conversation.id;
          setConversationId(id);
        }
        const reply = await chatApi.sendMessage(id, content);
        setMessages((prev) => [...prev, reply]);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Nachricht konnte nicht gesendet werden.");
      } finally {
        setSending(false);
      }
    },
    [conversationId, input, sending],
  );

  return (
    <div className="flex h-full flex-col rounded-lg border border-zinc-200 dark:border-zinc-800">
      <div className="border-b border-zinc-200 p-3 dark:border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Einrichtungshilfe</h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          Frag z.B. &bdquo;Wo finde ich meine CalDAV-URL?&ldquo; oder &bdquo;Wie erstelle ich ein
          Home-Assistant-Token?&ldquo;
        </p>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {loading ? (
          <p className="text-sm text-zinc-500">Lade...</p>
        ) : messages.length === 0 ? (
          <p className="text-sm text-zinc-500">Noch keine Fragen gestellt.</p>
        ) : (
          messages
            .filter((m) => m.role !== "tool")
            .map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-indigo-500 text-white"
                      : "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))
        )}
        {sending ? <p className="text-sm text-zinc-500">Denke nach...</p> : null}
        <div ref={bottomRef} />
      </div>
      {error ? (
        <div className="px-3 pb-1">
          <ErrorMessage message={error} />
        </div>
      ) : null}
      <form onSubmit={handleSend} className="flex items-center gap-2 border-t border-zinc-200 p-3 dark:border-zinc-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Frage stellen..."
          className="flex-1 rounded-md border border-zinc-300 px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          Senden
        </button>
      </form>
    </div>
  );
}
