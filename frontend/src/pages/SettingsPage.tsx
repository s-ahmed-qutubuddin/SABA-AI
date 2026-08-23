import { PageHeader, PageShell } from "../components/shared/PageHeader";
import { useVoiceState } from "../state/VoiceStateContext";
import { WS_URL } from "../services/api";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const { connected } = useVoiceState();

  const Row = ({ label, value }: { label: string; value: string }) => (
    <div className="flex items-center justify-between border-b border-white/[0.04] py-3.5 text-sm last:border-0">
      <span className="text-text-dim">{label}</span>
      <span className="font-mono text-xs text-text">{value}</span>
    </div>
  );

  return (
    <PageShell>
      <PageHeader eyebrow="DIAGNOSTICS · 06" title="Settings" />
      <div className="glass-card rounded-2xl px-5 shadow-glass">
        <Row label="API base URL" value={BASE_URL} />
        <Row label="WebSocket URL" value={WS_URL} />
        <Row label="Connection" value={connected ? "Connected" : "Offline"} />
        <Row label="Voice activation" value="Continuous — no wake word" />
        <Row label="AI routing" value="OmniRoute-compatible / backend-controlled" />
        <Row label="TTS voice" value="Gemini Live voice" />
        <details className="border-b border-white/[0.04] py-3.5 text-sm last:border-0">
          <summary className="cursor-pointer text-text-dim">Created by AQUS-AIE</summary>
          <div className="pt-3 font-mono text-xs text-text">AHMED QUTUBUDDIN SAAD AI ENGINEER</div>
        </details>
      </div>
      <p className="mt-4 text-xs text-text-dim">
        These reflect the current backend configuration in <code className="text-text">config.py</code> and{" "}
        <code className="text-text">ai.py</code>. Changing them requires editing those files directly — this page
        is read-only by design, to avoid a frontend settings screen silently drifting from what the backend
        actually runs.
      </p>
    </PageShell>
  );
}
