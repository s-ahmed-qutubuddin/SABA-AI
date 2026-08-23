import { useEffect, useMemo, useState } from "react";
import { Activity, Cpu, RefreshCcw, Router, ShieldCheck, Thermometer, WashingMachine } from "lucide-react";
import { api } from "../services/api";
import type { DeviceSummary } from "../types";
import { PageHeader, PageShell } from "../components/shared/PageHeader";

function providerLabel(provider: string) {
  if (provider === "smartthings") return "SmartThings";
  if (provider === "lg_thinq") return "LG ThinQ";
  if (provider === "ir") return "IR";
  return provider;
}

function DeviceGlyph({ type }: { type?: string }) {
  const t = (type || "").toLowerCase();
  if (t.includes("air") || t.includes("climate")) return <Thermometer size={18} />;
  if (t.includes("washer")) return <WashingMachine size={18} />;
  return <Cpu size={18} />;
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [providers, setProviders] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.listDevices();
      setDevices(data.devices || []);
      setProviders(data.provider_status || {});
      setErrors(data.errors || []);
    } catch (e) {
      setErrors([String(e)]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const openDevice = async (d: DeviceSummary) => {
    const key = `${d.provider}:${d.id}`;
    if (openId === key) { setOpenId(null); return; }
    setOpenId(key);
    if (!details[key]) {
      try {
        const data = await api.deviceCapabilities(d.provider, d.id);
        setDetails(prev => ({ ...prev, [key]: data }));
      } catch (e) {
        setResult(prev => ({ ...prev, [key]: String(e) }));
      }
    }
  };

  const runCommand = async (d: DeviceSummary, capability: string, command: string, args: any[], component: string) => {
    const key = `${d.provider}:${d.id}`;
    setBusy(`${key}:${capability}.${command}`);
    try {
      const data = await api.controlDevice(d.provider, d.id, { capability, command, arguments: args, component });
      setResult(prev => ({ ...prev, [key]: data.ok ? `✓ ${capability}.${command}` : JSON.stringify(data) }));
      const refreshed = await api.deviceCapabilities(d.provider, d.id);
      setDetails(prev => ({ ...prev, [key]: refreshed }));
    } catch (e) {
      setResult(prev => ({ ...prev, [key]: String(e) }));
    } finally {
      setBusy(null);
    }
  };

  const groups = useMemo(() => {
    const map = new Map<string, DeviceSummary[]>();
    for (const d of devices) map.set(d.provider, [...(map.get(d.provider) || []), d]);
    return map;
  }, [devices]);

  return (
    <PageShell>
      <PageHeader eyebrow="HOME · DEVICES" title="Devices" />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_320px]">
        <section className="space-y-3">
          <div className="flex items-center justify-between rounded-2xl border border-white/[.06] bg-white/[.02] px-4 py-3">
            <div className="flex items-center gap-3"><Router size={17} className="text-[#e7c96f]" /><span className="text-sm text-white">Connected devices</span></div>
            <button onClick={() => void load()} className="icon-button" aria-label="Refresh devices"><RefreshCcw size={16} className={loading ? "animate-spin" : ""} /></button>
          </div>
          {[...groups.entries()].map(([provider, list]) => (
            <div key={provider} className="space-y-2">
              <div className="section-label">{providerLabel(provider)}</div>
              {list.map((d) => (
                <div key={`${d.provider}:${d.id}`} className="glass-card rounded-2xl px-4 py-4">
                  <div className="flex items-center justify-between gap-4">
                    <button onClick={() => void openDevice(d)} className="flex min-w-0 items-center gap-3 text-left">
                      <div className="device-icon"><DeviceGlyph type={d.type} /></div>
                      <div className="min-w-0">
                        <div className="font-medium text-white">{d.name}</div>
                        <div className="mt-1 text-xs text-[#8d8797]">{d.model || d.type || "Device"}</div>
                      </div>
                    </button>
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className={d.online === false ? "status-badge offline" : "status-badge"}>{d.online === false ? "OFFLINE" : "READY"}</span>
                    </div>
                  </div>
                  {openId === `${d.provider}:${d.id}` && details[`${d.provider}:${d.id}`] && (
                    <div className="mt-4 border-t border-white/[.06] pt-4">
                      <div className="section-label">CONTROLS</div>
                      <div className="mt-3 space-y-3">
                        {(details[`${d.provider}:${d.id}`].controls || []).map((c: any) => (
                          <div key={`${c.component}:${c.capability}`} className="rounded-xl border border-white/[.05] bg-white/[.02] p-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-mono text-[#b8b2c3]">{c.capability}</span>
                              {c.read_only && <span className="text-[10px] uppercase text-[#8d8797]">read-only</span>}
                            </div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {(c.commands || []).filter((cmd: any) => cmd.available).map((cmd: any) => {
                                const argCount = (cmd.arguments || []).length;
                                return <button key={cmd.name} disabled={busy !== null} onClick={() => {
                                  const rawArgs = argCount === 0 ? "[]" : prompt(`Arguments for ${c.capability}.${cmd.name} as JSON array`, "[]");
                                  if (rawArgs === null) return;
                                  let parsed: any[];
                                  try {
                                    const decoded = JSON.parse(rawArgs);
                                    if (!Array.isArray(decoded)) throw new Error("Arguments must be a JSON array");
                                    parsed = decoded;
                                  } catch { setResult(prev => ({ ...prev, [`${d.provider}:${d.id}`]: "Invalid JSON arguments" })); return; }
                                  void runCommand(d, c.capability, cmd.name, parsed, c.component);
                                }} className="rounded-lg border border-white/[.08] px-2.5 py-1.5 text-xs text-white hover:bg-white/[.05] disabled:opacity-50">{cmd.name}</button>;
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                      {result[`${d.provider}:${d.id}`] && <div className="mt-3 text-xs text-[#57e7ff]">{result[`${d.provider}:${d.id}`]}</div>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
          {!loading && devices.length === 0 && <div className="glass-card rounded-2xl p-8 text-center text-sm text-[#8d8797]">No devices discovered yet. Connect SmartThings/LG or add the IR adapter.</div>}
        </section>

        <aside className="space-y-3">
          <div className="glass-card rounded-2xl p-4">
            <div className="section-label">INTEGRATION HEALTH</div>
            <div className="mt-3 space-y-3">
              {Object.entries(providers).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-[#b8b2c3]">{providerLabel(key)}</span>
                  <span className="font-mono text-xs text-[#e7c96f]">{value.toUpperCase()}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="glass-card rounded-2xl p-4">
            <div className="section-label">SAFETY</div>
            <div className="mt-3 flex gap-3 text-sm text-[#b8b2c3]"><ShieldCheck size={17} className="shrink-0 text-[#57e7ff]" /><span>Unsupported device capabilities are not exposed as working controls.</span></div>
          </div>
          {errors.length > 0 && <div className="glass-card rounded-2xl p-4"><div className="section-label">PROVIDER NOTES</div><div className="mt-3 space-y-2 text-xs text-[#ffb5c1]">{errors.map((e, i) => <div key={i}>{e}</div>)}</div></div>}
        </aside>
      </div>
    </PageShell>
  );
}
