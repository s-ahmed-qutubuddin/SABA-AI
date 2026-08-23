import { useState } from "react";
import { Brain, Trash2, Plus } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/shared/States";
import { useFetch } from "../state/useFetch";
import { api } from "../services/api";
import { Memory } from "../types";

function ImportanceMeter({ value }: { value: number }) {
  const dots = Array.from({ length: 10 });
  return (
    <div className="flex items-center gap-[3px]" aria-label={`Importance ${value} of 10`}>
      {dots.map((_, i) => (
        <span
          key={i}
          className={`h-1 w-1 rounded-full ${i < value ? "bg-signal" : "bg-white/10"}`}
        />
      ))}
    </div>
  );
}

export default function MemoriesPage() {
  const { data: memories, loading, error, reload, setData } = useFetch(() => api.listMemories(), []);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleAdd = async () => {
    if (!draft.trim()) return;
    setSubmitting(true);
    try {
      await api.addMemory(draft.trim());
      setDraft("");
      reload();
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    setData((prev) => (prev ? prev.filter((m) => m.memory_id !== id) : prev));
    await api.deleteMemory(id).catch(() => reload());
  };

  return (
    <PageShell>
      <PageHeader
        eyebrow="LONG-TERM MEMORY · 02"
        title="Memories"
        readout={memories ? `${memories.length} STORED` : undefined}
      />

      <div className="mb-6 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Something Saba should remember…"
          className="flex-1 rounded-xl border border-panel-border bg-panel-2/60 px-4 py-2.5 text-sm text-text placeholder:text-text-dim focus:border-signal/40"
        />
        <button
          onClick={handleAdd}
          disabled={submitting || !draft.trim()}
          className="flex items-center gap-1.5 rounded-xl border border-panel-border px-4 py-2.5 text-xs text-text transition hover:border-signal/40 hover:text-signal disabled:opacity-40"
        >
          <Plus size={14} /> Save
        </button>
      </div>

      {loading && <LoadingState label="Loading memories" />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && memories && memories.length === 0 && (
        <EmptyState icon={Brain} title="No memories yet" hint='Say "remember …" or add one above.' />
      )}

      {!loading && !error && memories && memories.length > 0 && (
        <ul className="flex flex-col gap-2">
          {memories.map((m: Memory) => (
            <li
              key={m.memory_id}
              className="glass-card group flex items-start justify-between gap-4 rounded-xl px-4 py-3 transition hover:border-signal/20"
            >
              <div>
                <div className="text-sm text-text">{m.memory}</div>
                <div className="mt-1.5 flex items-center gap-3 font-mono text-[10px] tracking-[0.15em] text-text-dim">
                  <span>{m.category.toUpperCase()}</span>
                  <ImportanceMeter value={m.importance} />
                </div>
              </div>
              <button
                onClick={() => handleDelete(m.memory_id)}
                className="shrink-0 text-text-dim opacity-0 transition hover:text-warn group-hover:opacity-100"
                aria-label={`Delete memory: ${m.memory}`}
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
