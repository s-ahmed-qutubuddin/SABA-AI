import { MessagesSquare, ArrowLeft } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/shared/States";
import { useFetch } from "../state/useFetch";
import { api } from "../services/api";
import { useState } from "react";

export default function ConversationsPage() {
  const { data: conversations, loading, error, reload } = useFetch(() => api.listConversations(), []);
  const [openId, setOpenId] = useState<number | null>(null);

  const {
    data: messages,
    loading: messagesLoading,
    error: messagesError,
  } = useFetch(() => (openId ? api.listMessages(openId) : Promise.resolve([])), [openId]);

  if (openId) {
    const conv = conversations?.find((c) => c.conversation_id === openId);
    return (
      <PageShell>
        <button
          onClick={() => setOpenId(null)}
          className="mb-4 flex items-center gap-1.5 text-xs text-text-dim transition hover:text-signal"
        >
          <ArrowLeft size={14} /> Back to conversations
        </button>
        <PageHeader eyebrow="SESSION LOG" title={conv?.title ?? "Conversation"} />

        {messagesLoading && <LoadingState label="Loading messages" />}
        {messagesError && <ErrorState message={messagesError} />}
        {!messagesLoading && !messagesError && messages && messages.length === 0 && (
          <EmptyState icon={MessagesSquare} title="No messages in this conversation yet" />
        )}
        {!messagesLoading && !messagesError && messages && messages.length > 0 && (
          <div className="flex flex-col gap-3">
            {messages.map((m) => (
              <div
                key={m.message_id}
                className={`glass-card max-w-lg rounded-2xl px-5 py-3.5 shadow-glass ${
                  m.role === "user" ? "self-end" : "self-start"
                }`}
              >
                <div
                  className={`mb-1 font-mono text-[10px] tracking-[0.2em] ${
                    m.role === "user" ? "text-text-dim" : "text-signal"
                  }`}
                >
                  {m.role === "user" ? "YOU" : "SABA"} · {new Date(m.created_at).toLocaleString()}
                </div>
                <div className="text-sm leading-relaxed text-text">{m.content}</div>
              </div>
            ))}
          </div>
        )}
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="SESSION HISTORY · 01"
        title="Conversations"
        readout={conversations ? `${conversations.length} LOGGED` : undefined}
      />

      {loading && <LoadingState label="Loading conversations" />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && conversations && conversations.length === 0 && (
        <EmptyState icon={MessagesSquare} title="No conversations yet" hint="Start listening from Home to begin one." />
      )}

      {!loading && !error && conversations && conversations.length > 0 && (
        <ul className="flex flex-col gap-2">
          {conversations.map((c) => (
            <li key={c.conversation_id}>
              <button
                onClick={() => setOpenId(c.conversation_id)}
                className="glass-card flex w-full items-center justify-between rounded-xl px-4 py-3 text-left transition hover:border-signal/30"
              >
                <div>
                  <div className="text-sm text-text">{c.title}</div>
                  <div className="mt-0.5 font-mono text-[10px] text-text-dim">
                    {new Date(c.updated_at).toLocaleString()}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
