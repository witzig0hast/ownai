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
  skill: string;
  updated_at: string;
}

export interface Skill {
  key: string;
  name: string;
  description: string;
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

export interface AgentIdentity {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export type AgentMessageKind = "text" | "task";
export type AgentMessageStatus = "sent" | "pending" | "in_progress" | "completed" | "failed";

export interface AgentMessage {
  id: string;
  from_label: string;
  to_label: string;
  kind: AgentMessageKind;
  content: string | null;
  task_type: string | null;
  payload: Record<string, unknown> | null;
  status: AgentMessageStatus;
  result: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  content: string;
  created_at: string;
}

export interface Contact {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  birthday_month: number | null;
  birthday_day: number | null;
  birthday_year: number | null;
  notes: string | null;
  created_at: string;
}

export type ReminderRecurrence = "daily" | "weekly" | "monthly";
export type Weekday = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";

export interface Reminder {
  id: string;
  label: string;
  recurrence: ReminderRecurrence;
  hour: number;
  minute: number;
  weekday: Weekday | null;
  day_of_month: number | null;
  active: boolean;
  created_at: string;
}

export interface Automation {
  id: string;
  entity_id: string;
  trigger_state: string;
  message: string;
  active: boolean;
  last_seen_state: string | null;
  created_at: string;
}

export type ListKind = "todo" | "shopping";

export interface ListItem {
  id: string;
  content: string;
  done: boolean;
  created_at: string;
}

export interface TodoList {
  id: string;
  name: string;
  kind: ListKind;
  created_at: string;
  items: ListItem[];
}

export interface Expense {
  id: string;
  amount: number;
  description: string;
  category: string | null;
  spent_at: string;
  created_at: string;
}

export interface ExpensesList {
  expenses: Expense[];
  total: number;
  by_category: Record<string, number>;
}

export interface DailyForecast {
  date: string;
  temp_min: number;
  temp_max: number;
  condition: string;
}

export interface Weather {
  location: string;
  country: string | null;
  current_temperature: number;
  current_condition: string;
  current_wind_speed: number;
  daily: DailyForecast[];
}

export interface RssFeed {
  id: string;
  url: string;
  name: string | null;
  created_at: string;
}

export interface RssItem {
  feed_name: string;
  title: string;
  link: string;
  published: string | null;
  summary: string | null;
}

export interface ClippedPage {
  title: string;
  url: string;
  text: string;
}

export interface Device {
  id: string;
  platform: "android" | "ios" | "web";
  label: string;
  created_at: string;
}

export interface GeneratedFile {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
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
