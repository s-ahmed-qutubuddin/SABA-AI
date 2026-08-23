import { Outlet } from "react-router-dom";
import { IconRail } from "../nav/IconRail";
import { useVoiceState } from "../../state/VoiceStateContext";

export function AppShell() {
  const { connected, lastError } = useVoiceState();

  return (
    <div className="app-shell">
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />
      <div className="vignette" />
      <div className="app-layout">
        <IconRail />
        <div className="app-frame">
          <header className="topbar">
            <div className="brand-lockup">
              <div>
                <div className="brand-name">JAMAL FAMILY</div>
                <div className="brand-sub">PRIVATE / FAMILY / INTELLIGENCE</div>
              </div>
            </div>
            <div className="topbar-right">
              <div className="topbar-chip">
                <span className={connected ? "pulse-dot" : "pulse-dot offline"} />
                {connected ? "BACKEND CONNECTED" : "BACKEND OFFLINE"}
              </div>
              <div className="topbar-chip">AI ROUTER</div>
            </div>
          </header>
          <main className="app-content">
            <Outlet />
          </main>
          {lastError && <div className="error-strip">{lastError}</div>}
        </div>
      </div>
    </div>
  );
}
