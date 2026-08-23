import { useEffect, useState } from "react";
import { TerminalSquare, Volume2, ShieldCheck, Play } from "lucide-react";
import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { LoadingState } from "../components/shared/States";
import { api } from "../services/api";

export default function SystemPage() {
  const [actions, setActions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("Ready");

  useEffect(() => {
    void api
      .allowedSystemActions()
      .then(({ actions }) => setActions(actions))
      .catch(() => setActions([]))
      .finally(() => setLoading(false));
  }, []);

  async function run(name: string) {
    setStatus(`${name}…`);
    try {
      if (name.startsWith("Open ")) await api.openApp(name.slice(5));
      else if (name === "Set volume") await api.setVolume(60);
      setStatus(`${name} completed`);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Action failed");
    }
  }

  return (
    <PageShell>
      <PageHeader
        eyebrow="CONTROL PLANE · 07"
        title="System"
        readout={actions.length ? `${actions.length} ALLOWED` : undefined}
        action={<ShieldCheck size={18} className="text-signal" />}
      />

      <p className="mb-7 max-w-2xl text-sm text-text-dim">
        Controlled local actions, executed by the backend on an explicit allowlist. The browser never runs a
        shell command directly — every action here goes through the same permission boundary as a spoken command.
      </p>

      {loading && <LoadingState label="Loading allowed actions" />}

      {!loading && (
        <div className="grid gap-3 sm:grid-cols-2">
          {actions.map((a) => (
            <button
              key={a}
              onClick={() => void run(a)}
              className="glass-card group rounded-2xl p-5 text-left transition hover:-translate-y-0.5 hover:border-signal/30 hover:shadow-glow-signal"
            >
              <div className="mb-8 flex items-center justify-between">
                <TerminalSquare className="text-signal" size={20} />
                <Play size={14} className="text-text-dim transition group-hover:text-signal" />
              </div>
              <div className="text-sm text-text">{a}</div>
              <div className="mt-1 font-mono text-[10px] tracking-[0.15em] text-text-dim">
                BACKEND-CONTROLLED
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="glass-card mt-7 flex items-center gap-3 rounded-2xl px-5 py-4">
        <Volume2 size={16} className="shrink-0 text-signal" />
        <span className="font-mono text-[10px] tracking-[0.2em] text-text-dim">STATUS</span>
        <span className="text-sm text-text">{status}</span>
      </div>
    </PageShell>
  );
}
