import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { LogOut, ShieldCheck, UserRound } from "lucide-react";
import { api, FamilyMember, SabaUser } from "./services/api";

interface CloudGateProps {
  children: ReactNode;
}

type GateStage = "checking" | "code" | "member" | "ready";

export default function CloudGate({ children }: CloudGateProps) {
  const [stage, setStage] = useState<GateStage>("checking");
  const [authRequired, setAuthRequired] = useState(true);
  const [code, setCode] = useState("");
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [user, setUser] = useState<SabaUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const owner = useMemo(() => members.find((member) => member.role === "owner"), [members]);

  const refreshSession = async () => {
    try {
      const session = await api.session();
      setAuthRequired(session.auth_required);
      if (session.authenticated) {
        setUser(session.user);
        setStage("ready");
        return;
      }
      setStage(session.auth_required ? "code" : "member");
      if (!session.auth_required) {
        const data = await api.members();
        setMembers(data.members);
      }
    } catch (err) {
      setError(String(err));
      setStage("code");
    }
  };

  useEffect(() => {
    void refreshSession();
  }, []);

  const submitCode = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.login(code);
      const data = await api.members();
      setMembers(data.members);
      setStage("member");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const chooseMember = async (member: FamilyMember) => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.selectMember(member.profile_id);
      setUser(result.user);
      setStage("ready");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const signOut = async () => {
    await api.logout().catch(() => undefined);
    setUser(null);
    setCode("");
    setStage(authRequired ? "code" : "member");
  };

  if (stage === "ready") {
    return (
      <div className="h-full w-full relative">
        {children}
        <button
          onClick={() => void signOut()}
          className="fixed right-4 bottom-4 z-50 flex items-center gap-2 rounded-full border border-white/10 bg-black/60 px-3 py-2 text-[11px] text-white/60 backdrop-blur-xl hover:text-white"
          aria-label="Switch Saba family member"
        >
          <span>{user?.preferred_name || user?.label || "Family"}</span>
          <LogOut size={13} />
        </button>
      </div>
    );
  }

  if (stage === "member") {
    return (
      <main className="cloud-gate-shell">
        <section className="cloud-gate-card">
          <div className="cloud-gate-kicker">JAMAL FAMILY ASSISTANT</div>
          <h1>SABA</h1>
          <p className="cloud-gate-copy">Choose who is using Saba on this device.</p>
          <div className="cloud-member-grid">
            {members.map((member) => (
              <button
                key={member.profile_id}
                onClick={() => void chooseMember(member)}
                disabled={busy}
                className={`cloud-member ${member.role === "owner" ? "cloud-member-owner" : ""}`}
              >
                <span className="cloud-member-icon"><UserRound size={18} /></span>
                <span className="cloud-member-text">
                  <strong>{member.preferred_name || member.label}</strong>
                  <span>{member.role === "owner" ? "Owner / Boss" : member.relationship_to_owner}</span>
                </span>
              </button>
            ))}
          </div>
          {owner && <div className="cloud-gate-note"><ShieldCheck size={15} /> {owner.preferred_name || owner.label} has owner-level controls.</div>}
          {error && <div className="cloud-gate-error">{error}</div>}
        </section>
      </main>
    );
  }

  return (
    <main className="cloud-gate-shell">
      <section className="cloud-gate-card">
        <div className="cloud-gate-kicker">JAMAL FAMILY ASSISTANT</div>
        <h1>SABA</h1>
        <p className="cloud-gate-copy">Enter the family access code.</p>
        <form onSubmit={(event) => { event.preventDefault(); void submitCode(); }}>
          <input
            autoFocus
            inputMode="numeric"
            type="password"
            value={code}
            maxLength={10}
            pattern="[0-9]{10}"
            onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 10))}
            className="cloud-code-input"
            placeholder="••••••••••"
            aria-label="Family access code"
          />
          {error && <div className="cloud-gate-error">{error}</div>}
          <button type="submit" disabled={busy || code.length !== 10} className="cloud-enter-button">
            {busy ? "CONNECTING…" : "ENTER SABA"}
          </button>
        </form>
        <div className="cloud-gate-note"><ShieldCheck size={15} /> Access is shared only with your family.</div>
      </section>
    </main>
  );
}
