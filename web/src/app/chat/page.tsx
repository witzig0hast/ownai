"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { VoicePicker } from "@/components/VoicePicker";
import { ApiError } from "@/lib/api-client";
import * as chatApi from "@/lib/api/chat";
import { isTtsSupported, speak, stopSpeaking, unlockSpeech } from "@/lib/tts";
import type { Conversation, Message } from "@/lib/types";
import { useVoiceRecorder } from "@/lib/useVoiceRecorder";

const AUTO_READ_STORAGE_KEY = "ownai.autoReadReplies";

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"
        stroke="currentColor"
        strokeWidth={active ? 2.5 : 2}
      />
      <path
        d="M19 11a7 7 0 0 1-14 0M12 18v3"
        stroke="currentColor"
        strokeWidth={active ? 2.5 : 2}
        strokeLinecap="round"
      />
    </svg>
  );
}

function SpeakerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
      <path
        d="M4 9v6h4l5 4V5L8 9H4Z"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <path d="M16.5 9a4 4 0 0 1 0 6" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ArchiveIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
      <path d="M4 7h16M6 7v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V7M10 11h4" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 4h18v3H3z" stroke="currentColor" strokeWidth={2} strokeLinejoin="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
      <path
        d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0v13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V7"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ConversationSidebar({
  conversations,
  selectedId,
  onSelect,
  onCreate,
  creating,
  loading,
  showArchived,
  onToggleShowArchived,
  onArchiveToggle,
  onDelete,
}: {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  creating: boolean;
  loading: boolean;
  showArchived: boolean;
  onToggleShowArchived: () => void;
  onArchiveToggle: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
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
      <label className="flex items-center gap-1.5 border-b border-zinc-200 px-3 py-2 text-xs text-zinc-500 dark:border-zinc-800">
        <input type="checkbox" checked={showArchived} onChange={onToggleShowArchived} className="h-3 w-3" />
        Archivierte anzeigen
      </label>
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <p className="p-3 text-sm text-zinc-500">Loading...</p>
        ) : conversations.length === 0 ? (
          <p className="p-3 text-sm text-zinc-500">No conversations yet. Start one above.</p>
        ) : (
          <ul>
            {conversations.map((c) => (
              <li key={c.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={`block w-full truncate px-3 py-2.5 pr-16 text-left text-sm transition-colors ${
                    c.id === selectedId
                      ? "bg-zinc-100 font-medium text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                      : "text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-900"
                  }`}
                >
                  <span className="block truncate">
                    {c.title || "Untitled conversation"}
                    {c.archived ? " (archiviert)" : ""}
                  </span>
                  <span className="block truncate text-xs text-zinc-400">
                    {formatTime(c.updated_at)}
                  </span>
                </button>
                <div className="absolute top-1/2 right-2 flex -translate-y-1/2 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onArchiveToggle(c);
                    }}
                    title={c.archived ? "Wiederherstellen" : "Archivieren"}
                    className="rounded p-1 text-zinc-400 hover:bg-zinc-200 hover:text-zinc-700 dark:hover:bg-zinc-700 dark:hover:text-zinc-200"
                  >
                    <ArchiveIcon />
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(c);
                    }}
                    title="Löschen"
                    className="rounded p-1 text-zinc-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-950 dark:hover:text-red-400"
                  >
                    <TrashIcon />
                  </button>
                </div>
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
        className={`group max-w-[75%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
            : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
        }`}
      >
        {message.content}
        {!isUser && isTtsSupported() ? (
          <button
            type="button"
            onClick={() => speak(message.content)}
            title="Antwort vorlesen"
            className="ml-2 inline-flex align-middle text-zinc-400 opacity-0 transition-opacity hover:text-zinc-700 group-hover:opacity-100 dark:hover:text-zinc-200"
          >
            <SpeakerIcon />
          </button>
        ) : null}
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
  const [showArchived, setShowArchived] = useState(false);

  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");

  const [listError, setListError] = useState<string | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);

  // Per-viewer convenience, not shared state — read once via a lazy initializer (not an
  // effect) so it's available on first render instead of causing an extra re-render.
  const [autoRead, setAutoRead] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.localStorage.getItem(AUTO_READ_STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });
  const voiceRecorder = useVoiceRecorder();

  const bottomRef = useRef<HTMLDivElement | null>(null);

  const toggleAutoRead = useCallback(() => {
    unlockSpeech(); // must run synchronously in this click handler - see tts.ts
    setAutoRead((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(AUTO_READ_STORAGE_KEY, String(next));
      } catch {
        // best-effort only
      }
      if (!next) stopSpeaking();
      return next;
    });
  }, []);

  const handleMicClick = useCallback(async () => {
    if (voiceRecorder.isRecording) {
      const text = await voiceRecorder.stopRecording();
      if (text) {
        setInput((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text));
      }
    } else {
      await voiceRecorder.startRecording();
    }
  }, [voiceRecorder]);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      setConversationsLoading(true);
      try {
        const list = await chatApi.listConversations(showArchived);
        if (cancelled) return;
        setConversations(list);
        if (!showArchived && list.length > 0) {
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
  }, [showArchived]);

  // Loads the model into Ollama ahead of time, so the first real reply on this screen doesn't
  // pay for the load - best-effort, a failure here shouldn't surface as a user-facing error.
  useEffect(() => {
    chatApi.warmup().catch(() => {});
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

  const handleArchiveToggle = useCallback(
    async (conversation: Conversation) => {
      setListError(null);
      try {
        const updated = await chatApi.updateConversation(conversation.id, { archived: !conversation.archived });
        setConversations((prev) => {
          const next = prev.map((c) => (c.id === updated.id ? updated : c));
          // Hide it immediately if it no longer matches the current filter, rather than
          // waiting for the next full reload.
          return showArchived ? next : next.filter((c) => !c.archived);
        });
        if (updated.archived && selectedId === updated.id) {
          setSelectedId(null);
        }
      } catch (err) {
        setListError(err instanceof ApiError ? err.message : "Failed to update conversation.");
      }
    },
    [showArchived, selectedId],
  );

  const handleDeleteConversation = useCallback(
    async (conversation: Conversation) => {
      const label = conversation.title || "diese Unterhaltung";
      if (!window.confirm(`${label} unwiderruflich löschen?`)) return;
      setListError(null);
      try {
        await chatApi.deleteConversation(conversation.id);
        setConversations((prev) => prev.filter((c) => c.id !== conversation.id));
        if (selectedId === conversation.id) {
          setSelectedId(null);
        }
      } catch (err) {
        setListError(err instanceof ApiError ? err.message : "Failed to delete conversation.");
      }
    },
    [selectedId],
  );

  const handleSend = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const content = input.trim();
      if (!content || !selectedId || sending) return;

      unlockSpeech(); // must run synchronously in this submit handler, before the awaits below - see tts.ts
      setSendError(null);
      const optimisticMessage: Message = {
        id: `local-${Date.now()}`,
        role: "user",
        content,
        tool_calls: null,
        created_at: new Date().toISOString(),
      };
      // Untitled conversations get an auto-generated title from this exchange server-side
      // (see API.md) - remember that so we know to refresh the title after the reply lands.
      const wasUntitled = conversations.find((c) => c.id === selectedId)?.title == null;

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
        if (wasUntitled) {
          chatApi
            .listConversations(showArchived)
            .then(setConversations)
            .catch(() => {});
        }
        if (autoRead) speak(assistantMessage.content);
      } catch (err) {
        setSendError(err instanceof ApiError ? err.message : "Failed to send message.");
      } finally {
        setSending(false);
      }
    },
    [input, selectedId, sending, autoRead, conversations, showArchived],
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
          showArchived={showArchived}
          onToggleShowArchived={() => setShowArchived((v) => !v)}
          onArchiveToggle={handleArchiveToggle}
          onDelete={handleDeleteConversation}
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
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-zinc-200 px-3 pt-2 dark:border-zinc-800">
                {isTtsSupported() ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="flex items-center gap-1.5 text-xs text-zinc-500">
                      <input type="checkbox" checked={autoRead} onChange={toggleAutoRead} className="h-3.5 w-3.5" />
                      Antworten automatisch vorlesen
                    </label>
                    <div className="w-48">
                      <VoicePicker />
                    </div>
                  </div>
                ) : (
                  <span />
                )}
                {voiceRecorder.error ? <ErrorMessage message={voiceRecorder.error} /> : null}
              </div>
              <form onSubmit={handleSend} className="flex items-end gap-2 p-3">
                {typeof navigator !== "undefined" && typeof navigator.mediaDevices?.getUserMedia === "function" ? (
                  <button
                    type="button"
                    onClick={handleMicClick}
                    disabled={voiceRecorder.isTranscribing || sending}
                    title={voiceRecorder.isRecording ? "Aufnahme beenden" : "Spracheingabe starten"}
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-md border transition-colors disabled:opacity-50 ${
                      voiceRecorder.isRecording
                        ? "animate-pulse border-red-500 bg-red-500 text-white"
                        : "border-zinc-300 text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    }`}
                  >
                    <MicIcon active={voiceRecorder.isRecording} />
                  </button>
                ) : null}
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend(e);
                    }
                  }}
                  placeholder={
                    voiceRecorder.isTranscribing
                      ? "Transkribiere..."
                      : voiceRecorder.isRecording
                        ? "Aufnahme läuft..."
                        : "Message OwnAI..."
                  }
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
