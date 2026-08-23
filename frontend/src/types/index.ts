export type SabaState = "idle" | "listening" | "thinking" | "tool_running" | "speaking" | "error" | "stopped" | "disconnected";

export interface ConversationTurn { role: "user" | "assistant"; text: string; at: number; }

export interface WsEvent {
  type: string;
  state?: SabaState;
  text?: string;
  message?: string;
  name?: string;
  role?: "user" | "assistant";
  result?: unknown;
  [key: string]: unknown;
}

export interface Conversation { conversation_id: number; title: string; created_at: string; updated_at: string; }
export interface Message { message_id: number; role: "user" | "assistant" | "system"; content: string; created_at: string; }
export interface Memory { memory_id: number; memory: string; category: string; importance: number; created_at: string; updated_at: string; }
export interface Note { note_id: number; title: string; content: string; created_at: string; updated_at: string; }
export type TaskStatus = "pending" | "completed";
export interface Task { task_id: number; title: string; description: string | null; status: TaskStatus; due_date: string | null; created_at: string; completed_at: string | null; }
export interface Preference { preference_id: number; preference_key: string; preference_value: string; created_at: string; updated_at: string; }

export interface DeviceSummary { provider: string; id: string; name: string; model?: string; type?: string; manufacturer?: string; online?: boolean | null; }
