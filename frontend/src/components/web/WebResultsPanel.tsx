import { Globe, ExternalLink } from "lucide-react";

export interface WebResult {
  title: string;
  url: string;
  snippet: string;
}

/**
 * Displays backend-provided web/news results inline with the conversation.
 * Prop contract unchanged: `results: WebResult[] | null`.
 */
export function WebResultsPanel({ results }: { results: WebResult[] | null }) {
  if (!results || results.length === 0) return null;

  return (
    <div className="glass-card mx-auto flex w-full max-w-xl flex-col gap-1 rounded-2xl p-4 shadow-glass">
      <div className="mb-1 flex items-center gap-2 font-mono text-[10px] tracking-[0.2em] text-text-dim">
        <Globe size={12} /> RESULTS FROM THE WEB
      </div>
      {results.map((r) => (
        <a
          key={r.url}
          href={r.url}
          target="_blank"
          rel="noreferrer"
          className="group flex items-start justify-between gap-3 rounded-xl px-2 py-2 transition hover:bg-white/[0.03]"
        >
          <div className="min-w-0">
            <div className="truncate text-sm text-text group-hover:text-signal">{r.title}</div>
            <div className="line-clamp-1 text-xs text-text-dim">{r.snippet}</div>
          </div>
          <ExternalLink size={12} className="mt-1 shrink-0 text-text-dim" />
        </a>
      ))}
    </div>
  );
}
