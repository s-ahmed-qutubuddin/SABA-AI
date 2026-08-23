import { useState } from "react";
import { StickyNote, Trash2, Plus, Pencil, X, Check } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/shared/States";
import { useFetch } from "../state/useFetch";
import { api } from "../services/api";
import { Note } from "../types";

export default function NotesPage() {
  const { data: notes, loading, error, reload, setData } = useFetch(() => api.listNotes(), []);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");

  const handleAdd = async () => {
    if (!title.trim()) return;
    await api.addNote(title.trim(), content.trim());
    setTitle("");
    setContent("");
    setShowForm(false);
    reload();
  };

  const startEdit = (note: Note) => {
    setEditingId(note.note_id);
    setEditTitle(note.title);
    setEditContent(note.content);
  };

  const saveEdit = async (id: number) => {
    await api.updateNote(id, editTitle.trim(), editContent.trim());
    setEditingId(null);
    reload();
  };

  const handleDelete = async (id: number) => {
    setData((prev) => (prev ? prev.filter((n) => n.note_id !== id) : prev));
    await api.deleteNote(id).catch(() => reload());
  };

  return (
    <PageShell>
      <PageHeader
        eyebrow="ARCHIVE · 03"
        title="Notes"
        readout={notes ? `${notes.length} SAVED` : undefined}
        action={
          <button
            onClick={() => setShowForm((s) => !s)}
            className="flex items-center gap-1.5 rounded-full border border-panel-border px-4 py-2 text-xs text-text transition hover:border-signal/40 hover:text-signal"
          >
            <Plus size={14} /> New note
          </button>
        }
      />

      {showForm && (
        <div className="glass-card mb-6 flex flex-col gap-2 rounded-2xl p-4 shadow-glass">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            className="rounded-lg border border-panel-border bg-panel-2/60 px-3 py-2 text-sm text-text placeholder:text-text-dim focus:border-signal/40"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Write something…"
            rows={3}
            className="rounded-lg border border-panel-border bg-panel-2/60 px-3 py-2 text-sm text-text placeholder:text-text-dim focus:border-signal/40"
          />
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs text-text-dim hover:text-text">
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!title.trim()}
              className="rounded-lg border border-panel-border px-3 py-1.5 text-xs text-signal disabled:opacity-40"
            >
              Save note
            </button>
          </div>
        </div>
      )}

      {loading && <LoadingState label="Loading notes" />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && notes && notes.length === 0 && (
        <EmptyState icon={StickyNote} title="No notes yet" hint='Say "note …" or create one above.' />
      )}

      {!loading && !error && notes && notes.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {notes.map((n: Note) => (
            <div key={n.note_id} className="glass-card group rounded-2xl p-4 transition hover:border-signal/20">
              {editingId === n.note_id ? (
                <div className="flex flex-col gap-2">
                  <input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="rounded-lg border border-panel-border bg-panel-2/60 px-3 py-1.5 text-sm text-text"
                  />
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={3}
                    className="rounded-lg border border-panel-border bg-panel-2/60 px-3 py-1.5 text-sm text-text"
                  />
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setEditingId(null)} className="text-text-dim hover:text-text">
                      <X size={16} />
                    </button>
                    <button onClick={() => saveEdit(n.note_id)} className="text-signal">
                      <Check size={16} />
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="mb-2 flex items-start justify-between">
                    <div className="font-display text-sm text-text">{n.title}</div>
                    <div className="flex gap-2 opacity-0 transition group-hover:opacity-100">
                      <button onClick={() => startEdit(n)} aria-label={`Edit ${n.title}`} className="text-text-dim hover:text-signal">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => handleDelete(n.note_id)} aria-label={`Delete ${n.title}`} className="text-text-dim hover:text-warn">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  <div className="text-sm leading-relaxed text-text-dim">{n.content}</div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </PageShell>
  );
}
