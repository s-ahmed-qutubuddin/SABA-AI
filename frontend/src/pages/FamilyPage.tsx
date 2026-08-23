import { ShieldCheck, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { api, FamilyMember } from "../services/api";
import { PageHeader, PageShell } from "../components/shared/PageHeader";

export default function FamilyPage() {
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listFamily().then(setMembers).catch((err) => setError(String(err))).finally(() => setLoading(false));
  }, []);

  return (
    <PageShell>
      <PageHeader eyebrow="FAMILY · IDENTITIES" title="Family" />
      <div className="space-y-3">
        <div className="glass-card rounded-2xl p-4 text-sm text-[#b8b2c3]">
          Every member has a separate Saba identity, conversations, memories, notes, tasks and preferences. Family context stays shared.
        </div>
        {loading && <div className="glass-card rounded-2xl p-6 text-sm text-[#8d8797]">Loading family profiles…</div>}
        {error && <div className="glass-card rounded-2xl p-6 text-sm text-[#ffb5c1]">{error}</div>}
        {!loading && members.map((member) => (
          <div key={member.profile_id} className={`glass-card rounded-2xl p-4 ${member.role === "owner" ? "border-[#e7c96f]/25" : ""}`}>
            <div className="flex items-center gap-3">
              <div className="device-icon"><UserRound size={18} /></div>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-white">{member.preferred_name || member.label}</div>
                <div className="mt-1 text-xs text-[#8d8797]">{member.label} · {member.relationship_to_owner}</div>
              </div>
              {member.role === "owner" && <span className="status-badge"><ShieldCheck size={12} className="inline mr-1" /> OWNER</span>}
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 text-xs text-[#b8b2c3]">
              <div><span className="text-[#777181]">Role:</span> {member.role_title || member.role}</div>
              <div><span className="text-[#777181]">User ID:</span> {member.user_id ?? "pending"}</div>
            </div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
