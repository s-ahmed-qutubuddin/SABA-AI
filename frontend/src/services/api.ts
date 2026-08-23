import { Conversation, Memory, Message, Note, Preference, Task } from "../types";

function runtimeHttpBase() {
  const configured = (import.meta.env.VITE_API_URL || "").trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:8000";
}

function runtimeWsBase(path: string) {
  const configured = (import.meta.env.VITE_WS_URL || "").trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}${path}`;
  }
  return `ws://localhost:8000${path}`;
}

const BASE_URL = runtimeHttpBase();

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Saba backend error (${res.status}): ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface SabaUser {
  user_id: number;
  owner_user_id: number;
  profile_id: number;
  role: "owner" | "family_member" | string;
  label: string;
  preferred_name?: string | null;
}

export interface FamilyMember {
  profile_id: number;
  user_id?: number | null;
  label: string;
  preferred_name?: string | null;
  relationship_to_owner: string;
  role_title?: string | null;
  role: "owner" | "family_member" | string;
}

export const api = {
  session: () => request<{ authenticated: boolean; auth_required: boolean; user: SabaUser | null }>("/auth/session"),
  login: (code: string) => request<{ ok: boolean; requires_member_selection: boolean }>("/auth/login", { method: "POST", body: JSON.stringify({ code }) }),
  members: () => request<{ owner_user_id: number; members: FamilyMember[] }>("/auth/members"),
  selectMember: (profile_id: number) => request<{ ok: boolean; user: SabaUser }>("/auth/select-member", { method: "POST", body: JSON.stringify({ profile_id }) }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () => request<{ user: SabaUser; profile: FamilyMember | null }>("/me"),
  voiceStatus: () => request<{ state: string; conversation_id: number | null }>('/voice/status'),
  health: () => request<{ status: string; database: string; gemini_text: string; gemini_live: string; lg_thinq: string; smartthings: string; omniroute: string; omniroute_model: string | null; ir?: any }>("/health"),
  chat: (conversationId: number | null, message: string) =>
    request<{ response: string; handled: boolean; conversation_id: number; events: unknown[] }>("/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, message }),
    }),
  listConversations: () => request<Conversation[]>("/conversations"),
  createConversation: (title?: string) => request<{ conversation_id: number }>(`/conversations?title=${encodeURIComponent(title || "Jamal Family Session")}`, { method: "POST" }),
  listMessages: (conversationId: number) => request<Message[]>(`/conversations/${conversationId}/messages`),
  listMemories: () => request<Memory[]>("/memories"),
  addMemory: (memory: string, category = "general", importance = 5) => request<{ memory_id: number }>("/memories", { method: "POST", body: JSON.stringify({ memory, category, importance }) }),
  deleteMemory: (id: number) => request<{ deleted: boolean }>(`/memories/${id}`, { method: "DELETE" }),
  listNotes: () => request<Note[]>("/notes"),
  addNote: (title: string, content: string) => request<{ note_id: number }>("/notes", { method: "POST", body: JSON.stringify({ title, content }) }),
  updateNote: (id: number, title: string, content: string) => request<{ updated: boolean }>(`/notes/${id}`, { method: "PUT", body: JSON.stringify({ title, content }) }),
  deleteNote: (id: number) => request<{ deleted: boolean }>(`/notes/${id}`, { method: "DELETE" }),
  listTasks: () => request<Task[]>("/tasks"),
  addTask: (title: string, description?: string, due_date?: string) => request<{ task_id: number }>("/tasks", { method: "POST", body: JSON.stringify({ title, description, due_date }) }),
  updateTask: (id: number, title: string, description: string | null, due_date: string | null, status: string) => request<{ updated: boolean }>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify({ title, description, due_date, status }) }),
  completeTask: (id: number) => request<{ updated: boolean }>(`/tasks/${id}/complete`, { method: "POST" }),
  deleteTask: (id: number) => request<{ deleted: boolean }>(`/tasks/${id}`, { method: "DELETE" }),
  allowedSystemActions: () => request<{ actions: string[]; role: string }>("/system/allowed"),
  openApp: (name: string) => request<{ label: string; app: string }>("/system/open-app", { method: "POST", body: JSON.stringify({ name }) }),
  setVolume: (percent: number) => request<{ label: string; volume: number }>("/system/volume", { method: "POST", body: JSON.stringify({ percent }) }),
  webSearch: (q: string) => request<{ title: string; url: string; snippet: string }[]>(`/web/search?q=${encodeURIComponent(q)}`),
  listDevices: () => request<{ ok: boolean; count: number; devices: Array<{ provider: string; id: string; name: string; model?: string; type?: string; manufacturer?: string; online?: boolean | null }>; provider_status: Record<string, string>; errors: string[] }>("/home/devices"),
  deviceStatus: (provider: string, deviceId: string) => request<any>(`/home/status?provider=${encodeURIComponent(provider)}&device_id=${encodeURIComponent(deviceId)}`),
  deviceCapabilities: (provider: string, deviceId: string) => request<any>(`/home/capabilities?provider=${encodeURIComponent(provider)}&device_id=${encodeURIComponent(deviceId)}`),
  controlDevice: (provider: string, deviceId: string, command: Record<string, unknown>) => request<any>("/home/control", { method: "POST", body: JSON.stringify({ provider, device_id: deviceId, command }) }),
  deviceEnergy: (provider: string, deviceId: string) => request<any>(`/home/energy?provider=${encodeURIComponent(provider)}&device_id=${encodeURIComponent(deviceId)}`),
  listPreferences: () => request<Preference[]>("/preferences"),
  setPreference: (key: string, value: string) => request<{ ok: true }>(`/preferences/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value }) }),
  listFamily: () => request<FamilyMember[]>("/family/profiles"),
};

export const WS_URL = runtimeWsBase("/ws/voice");
export const ACTIVATION_WS_URL = runtimeWsBase("/ws/activation");
