import { useState } from "react";
import { SlidersHorizontal, Plus } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/shared/States";
import { useFetch } from "../state/useFetch";
import { api } from "../services/api";

export default function PreferencesPage() {
  const { data: prefs, loading, error, reload } = useFetch(() => api.listPreferences(), []);
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

  const handleAdd = async () => {
    if (!key.trim() || !value.trim()) return;
    await api.setPreference(key.trim(), value.trim());
    setKey("");
    setValue("");
    reload();
  };

  const handleSaveEdit = async (k: string) => {
    await api.setPreference(k, editingValue.trim());
    setEditingKey(null);
    reload();
  };

  return (
    <PageShell>
      <PageHeader
        eyebrow="CONFIGURATION · 05"
        title="Preferences"
        readout={prefs ? `${prefs.length} SET` : undefined}
      />

      <div className="mb-6 flex gap-2">
        <input
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="key (e.g. theme)"
          className="w-40 rounded-xl border border-panel-border bg-panel-2/60 px-3 py-2.5 text-sm text-text placeholder:text-text-dim focus:border-signal/40"
        />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="value (e.g. dark)"
          className="flex-1 rounded-xl border border-panel-border bg-panel-2/60 px-3 py-2.5 text-sm text-text placeholder:text-text-dim focus:border-signal/40"
        />
        <button
          onClick={handleAdd}
          disabled={!key.trim() || !value.trim()}
          className="flex items-center gap-1.5 rounded-xl border border-panel-border px-4 py-2.5 text-xs text-text transition hover:border-signal/40 hover:text-signal disabled:opacity-40"
        >
          <Plus size={14} /> Set
        </button>
      </div>

      {loading && <LoadingState label="Loading preferences" />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && prefs && prefs.length === 0 && (
        <EmptyState
          icon={SlidersHorizontal}
          title="No preferences set"
          hint='Say "preference theme: dark" or set one above.'
        />
      )}

      {!loading && !error && prefs && prefs.length > 0 && (
        <ul className="flex flex-col gap-2">
          {prefs.map((p) => (
            <li
              key={p.preference_id}
              className="glass-card flex items-center justify-between gap-4 rounded-xl px-4 py-3 transition hover:border-signal/20"
            >
              <div className="font-mono text-xs tracking-wide text-text-dim">{p.preference_key}</div>
              {editingKey === p.preference_key ? (
                <input
                  autoFocus
                  value={editingValue}
                  onChange={(e) => setEditingValue(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSaveEdit(p.preference_key)}
                  onBlur={() => handleSaveEdit(p.preference_key)}
                  className="rounded-lg border border-signal/40 bg-panel-2/60 px-2 py-1 text-sm text-text"
                />
              ) : (
                <button
                  onClick={() => {
                    setEditingKey(p.preference_key);
                    setEditingValue(p.preference_value);
                  }}
                  className="rounded-lg px-2 py-1 text-sm text-text transition hover:bg-white/[0.04]"
                >
                  {p.preference_value}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
