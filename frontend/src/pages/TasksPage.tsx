import { useMemo, useState } from "react";
import { ListChecks, Trash2, Plus, Check, Clock } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/shared/States";
import { useFetch } from "../state/useFetch";
import { api } from "../services/api";
import { Task } from "../types";

function isOverdue(task: Task) {
  if (task.status === "completed" || !task.due_date) return false;
  return new Date(task.due_date).getTime() < Date.now();
}

export default function TasksPage() {
  const { data: tasks, loading, error, reload, setData } = useFetch(() => api.listTasks(), []);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");

  const grouped = useMemo(() => {
    if (!tasks) return null;
    return {
      overdue: tasks.filter(isOverdue),
      pending: tasks.filter((t) => t.status === "pending" && !isOverdue(t)),
      completed: tasks.filter((t) => t.status === "completed"),
    };
  }, [tasks]);

  const handleAdd = async () => {
    if (!title.trim()) return;
    await api.addTask(title.trim(), undefined, dueDate || undefined);
    setTitle("");
    setDueDate("");
    reload();
  };

  const handleComplete = async (id: number) => {
    setData((prev) => (prev ? prev.map((t) => (t.task_id === id ? { ...t, status: "completed" } : t)) : prev));
    await api.completeTask(id).catch(() => reload());
  };

  const handleDelete = async (id: number) => {
    setData((prev) => (prev ? prev.filter((t) => t.task_id !== id) : prev));
    await api.deleteTask(id).catch(() => reload());
  };

  const Section = ({ label, items, tone }: { label: string; items: Task[]; tone: "warn" | "signal" | "dim" }) => {
    if (items.length === 0) return null;
    const toneClass = tone === "warn" ? "text-warn" : tone === "signal" ? "text-signal" : "text-text-dim";
    return (
      <div className="mb-7">
        <div className={`mb-2.5 flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] ${toneClass}`}>
          <span className={`h-1 w-1 rounded-full ${tone === "warn" ? "bg-warn" : tone === "signal" ? "bg-signal" : "bg-text-dim"}`} />
          {label.toUpperCase()} — {items.length}
        </div>
        <ul className="flex flex-col gap-2">
          {items.map((t) => (
            <li
              key={t.task_id}
              className="glass-card group flex items-center justify-between gap-4 rounded-xl px-4 py-3 transition hover:border-signal/20"
            >
              <div className="flex items-center gap-3">
                {t.status !== "completed" && (
                  <button
                    onClick={() => handleComplete(t.task_id)}
                    aria-label={`Mark "${t.title}" complete`}
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-panel-border text-transparent transition hover:border-signal hover:text-signal hover:shadow-[0_0_8px_1px_color-mix(in srgb, var(--accent) 40%, transparent)]"
                  >
                    <Check size={12} />
                  </button>
                )}
                {t.status === "completed" && (
                  <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-signal-dim text-ink">
                    <Check size={12} />
                  </div>
                )}
                <div>
                  <div className={`text-sm ${t.status === "completed" ? "text-text-dim line-through" : "text-text"}`}>
                    {t.title}
                  </div>
                  {t.due_date && (
                    <div className="mt-0.5 flex items-center gap-1 font-mono text-[10px] text-text-dim">
                      <Clock size={10} /> {new Date(t.due_date).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleDelete(t.task_id)}
                aria-label={`Delete "${t.title}"`}
                className="shrink-0 text-text-dim opacity-0 transition hover:text-warn group-hover:opacity-100"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <PageShell>
      <PageHeader
        eyebrow="INSTRUMENT · 04"
        title="Tasks"
        readout={grouped ? `${grouped.pending.length + grouped.overdue.length} OPEN` : undefined}
      />

      <div className="mb-7 flex flex-wrap gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="New task…"
          className="flex-1 rounded-xl border border-panel-border bg-panel-2/60 px-4 py-2.5 text-sm text-text placeholder:text-text-dim focus:border-signal/40"
        />
        <input
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="rounded-xl border border-panel-border bg-panel-2/60 px-3 py-2.5 text-sm text-text focus:border-signal/40"
        />
        <button
          onClick={handleAdd}
          disabled={!title.trim()}
          className="flex items-center gap-1.5 rounded-xl border border-panel-border px-4 py-2.5 text-xs text-text transition hover:border-signal/40 hover:text-signal disabled:opacity-40"
        >
          <Plus size={14} /> Add
        </button>
      </div>

      {loading && <LoadingState label="Loading tasks" />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && tasks && tasks.length === 0 && (
        <EmptyState icon={ListChecks} title="No tasks yet" hint='Say "task …" or add one above.' />
      )}

      {!loading && !error && grouped && (
        <>
          <Section label="Overdue" items={grouped.overdue} tone="warn" />
          <Section label="Pending" items={grouped.pending} tone="signal" />
          <Section label="Completed" items={grouped.completed} tone="dim" />
        </>
      )}
    </PageShell>
  );
}
