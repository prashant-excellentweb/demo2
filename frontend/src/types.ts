/** Mirrors the Pydantic schemas in `app/schemas`. */

export interface User {
  id: string;
  username: string;
  display_name: string | null;
  created_at: string;
}

export interface DailyUsage {
  tokens_used: number;
  daily_budget: number;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Source {
  title: string;
  url: string;
  snippet: string;
}

export interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  is_image: boolean;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  sources: Source[] | null;
  attachments: Attachment[];
}

/** Sidebar projection: deliberately carries no message bodies. */
export interface ChatSummary {
  id: string;
  title: string;
  project_id: string | null;
  total_tokens: number;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatDetail {
  id: string;
  title: string;
  project_id: string | null;
  total_tokens: number;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface SendMessagePayload {
  content: string;
  attachment_ids?: string[];
  web_search?: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface EphemeralTurn {
  role: MessageRole;
  content: string;
}
