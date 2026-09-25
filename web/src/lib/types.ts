// Types mirroring the API contract in /API.md. Field names and shapes are
// kept identical to the contract so payloads can be passed through as-is.

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface Conversation {
  id: string;
  title: string | null;
  updated_at: string;
}

export interface ToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
}

export type MessageRole = "user" | "assistant" | "tool";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  tool_calls: ToolCall[] | null;
  created_at: string;
}

export type EventSource = "caldav";

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location: string | null;
  source: EventSource;
}

export type SuggestionKind = "calendar_event" | "reply_draft";
export type SuggestionStatus = "open" | "applied" | "dismissed";

export interface Suggestion {
  id: string;
  notification_id: string;
  kind: SuggestionKind;
  summary: string;
  payload: Record<string, unknown>;
  status: SuggestionStatus;
  created_at: string;
}
