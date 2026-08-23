import { useState } from "react";
import { Globe2, Search, ExternalLink } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { api } from "../services/api";

interface WebResult {
  title: string;
  url: string;
  snippet: string;
}

export default function WebPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<WebResult[]>([]);
  const [busy, setBusy] = useState(false);

  async function go() {
    if (!q.trim()) return;
    setBusy(true);
    try {
      setResults(await api.webSearch(q));
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell>
      <PageHeader eyebrow="INTERNET LAYER · 08" title="Web Access" />

      <p className="mb-7 max-w-2xl text-sm text-text-dim">
        Search current information through the Saba backend. Sources stay visible and the client holds no
        credentials — the same path a spoken "search…" command uses.
      </p>

      <div className="mb-7 flex gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void go()}
          placeholder="Search the web…"
          className="flex-1 rounded-2xl border border-panel-border bg-panel-2/60 px-4 py-3 text-sm text-text placeholder:text-text-dim outline-none focus:border-signal/40"
        />
        <button
          onClick={() => void go()}
          disabled={busy || !q.trim()}
          className="flex items-center justify-center rounded-2xl border border-signal/30 bg-signal/10 px-5 text-signal transition hover:bg-signal/15 disabled:opacity-40"
        >
          {busy ? <span className="font-mono text-xs">···</span> : <Search size={16} />}
        </button>
      </div>

      <div className="grid gap-3">
        {results.map((r) => (
          <a
            key={r.url}
            href={r.url}
            target="_blank"
            rel="noreferrer"
            className="glass-card group rounded-2xl p-5 transition hover:border-signal/30"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-mono text-[10px] tracking-[0.2em] text-text-dim">SOURCE</div>
                <div className="mt-1.5 text-base text-text group-hover:text-signal">{r.title}</div>
                <p className="mt-1.5 text-sm text-text-dim">{r.snippet}</p>
                <div className="mt-2 truncate text-xs text-signal/80">{r.url}</div>
              </div>
              <ExternalLink size={14} className="mt-1 shrink-0 text-text-dim group-hover:text-signal" />
            </div>
          </a>
        ))}

        {!results.length && (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-panel-border py-16 text-center">
            <Globe2 className="text-signal/70" size={26} strokeWidth={1.25} />
            <div className="text-sm text-text-dim">Search results will appear here.</div>
          </div>
        )}
      </div>
    </PageShell>
  );
}
