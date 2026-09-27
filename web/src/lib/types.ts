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
  is_admin: boolean;
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
  archived: boolean;
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

export interface Timer {
  id: string;
  label: string | null;
  ends_at: string;
}

export interface AppSettings {
  registration_open: boolean;
  system_paused: boolean;
  system_paused_message: string | null;
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
