import type { CSSProperties } from "react";
import { SabaState } from "../../types";

const LABEL: Record<SabaState, string> = {
  idle: "READY",
  listening: "LISTENING",
  thinking: "THINKING",
  tool_running: "TOOL RUNNING",
  speaking: "SPEAKING",
  error: "ATTENTION",
  stopped: "DORMANT",
  disconnected: "RECONNECTING",
};
const COLOR: Record<SabaState, string> = {
  idle: "#7B61FF",
  listening: "#38E7FF",
  thinking: "#B35CFF",
  tool_running: "#F0C85A",
  speaking: "#F0C85A",
  error: "#FF4C7A",
  stopped: "#7E8294",
  disconnected: "#F0C85A",
};
const SPEED: Record<SabaState, number> = {
  idle: 1,
  listening: 1.5,
  thinking: 2.15,
  tool_running: 1.8,
  speaking: 1.8,
  error: 0.55,
  stopped: 0.35,
  disconnected: 0.9,
};
function seeded(seed: number) {
  const x = Math.sin(seed * 177.31) * 43758.5453;
  return x - Math.floor(x);
}
function getSafeState(state: SabaState): SabaState {
  return Object.prototype.hasOwnProperty.call(LABEL, state) ? state : "idle";
}
export function SabaOrb({ state }: { state: SabaState }) {
  const safeState = getSafeState(state);
  const color = COLOR[safeState];
  const speed = SPEED[safeState];
  const particleCount = 220;
  const latitudes = 18;
  const meridians = 20;
  const particles = Array.from({ length: particleCount }, (_, i) => {
    const a = seeded(i + 1.7) * Math.PI * 2;
    const band = seeded(i + 7.4);
    const r = 150 + band * 56 + Math.sin(a * 4.5) * 5;
    return { x: 250 + Math.cos(a) * r, y: 250 + Math.sin(a) * r * (0.88 + seeded(i + 10) * 0.18), size: 0.6 + seeded(i + 4) * 1.8, opacity: 0.2 + seeded(i + 19) * 0.7, delay: `${(i % 19) * 0.08}s` };
  });
  const meridianD = Array.from({ length: meridians }, (_, i) => {
    const t = i / (meridians - 1) - 0.5;
    const x = 250 + t * 220;
    const bend = 24 + Math.abs(t) * 48;
    return `M ${x.toFixed(1)} 100 C ${(x + bend).toFixed(1)} 155 ${(x - bend * 0.7).toFixed(1)} 330 ${(250 - t * 18).toFixed(1)} 400`;
  });
  const latitudeD = Array.from({ length: latitudes }, (_, i) => {
    const y = 108 + i * 16.1;
    const depth = Math.sin((i / (latitudes - 1)) * Math.PI) * 32;
    const lean = Math.sin(i * 0.85) * 5;
    return `M 104 ${y.toFixed(1)} Q 176 ${(y - depth + lean).toFixed(1)} 250 ${y.toFixed(1)} Q 324 ${(y + depth - lean).toFixed(1)} 396 ${y.toFixed(1)}`;
  });
  const wavePaths = [0, 1, 2, 3].map((i) => {
    const y = 210 + i * 24;
    const bend = 48 + i * 7;
    return `M 120 ${y} C 170 ${y - bend} 212 ${y + bend} 266 ${y - 4} S 356 ${y - bend} 386 ${y + 8}`;
  });
  const orbStyle = { "--orb-color": color, "--orb-speed": speed } as CSSProperties;
  return (
    <div className={`saba-orb orb-${safeState}`} style={orbStyle} aria-label={`Saba ${LABEL[safeState].toLowerCase()}`}>
      <div className="orb-glow orb-glow-a" /><div className="orb-glow orb-glow-b" /><div className="orb-aura-ring orb-aura-ring-a" /><div className="orb-aura-ring orb-aura-ring-b" />
      <svg className="orb-art" viewBox="0 0 500 500" aria-hidden="true">
        <defs>
          <radialGradient id="sabaBlob" cx="42%" cy="36%" r="72%"><stop offset="0%" stopColor="#E7F7FF" stopOpacity="0.42"/><stop offset="18%" stopColor="#69D8FF" stopOpacity="0.24"/><stop offset="42%" stopColor="#7B61FF" stopOpacity="0.2"/><stop offset="72%" stopColor="#B338FF" stopOpacity="0.13"/><stop offset="100%" stopColor="#190A2E" stopOpacity="0"/></radialGradient>
          <linearGradient id="sabaMesh" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor="#40E9FF"/><stop offset="48%" stopColor="#796BFF"/><stop offset="100%" stopColor="#F052FF"/></linearGradient>
          <linearGradient id="sabaEdge" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#32E8FF"/><stop offset="50%" stopColor="#6F7CFF"/><stop offset="100%" stopColor="#FF4FD8"/></linearGradient>
          <filter id="sabaBlur" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="7"/></filter>
          <filter id="sabaLineGlow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="1.3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
          <clipPath id="sabaBlobClip"><path d="M 121 246 C 106 192 132 136 178 115 C 233 90 290 103 334 118 C 382 133 402 180 395 229 C 390 272 411 307 382 346 C 352 386 297 400 246 391 C 193 382 130 375 111 329 C 96 293 132 277 121 246 Z"/></clipPath>
        </defs>
        <ellipse cx="250" cy="258" rx="138" ry="146" fill="url(#sabaBlob)" filter="url(#sabaBlur)" opacity="0.85"/>
        <g className="orb-organic-shell">
          <path d="M 121 246 C 106 192 132 136 178 115 C 233 90 290 103 334 118 C 382 133 402 180 395 229 C 390 272 411 307 382 346 C 352 386 297 400 246 391 C 193 382 130 375 111 329 C 96 293 132 277 121 246 Z" fill="rgba(8,7,18,.45)" stroke="url(#sabaEdge)" strokeWidth="1.3" strokeOpacity="0.55"/>
          <g clipPath="url(#sabaBlobClip)" fill="none" stroke="url(#sabaMesh)" strokeWidth="1.15" strokeOpacity="0.64" filter="url(#sabaLineGlow)">{meridianD.map((d,i)=><path key={`md-${i}`} d={d} className="mesh-drift" style={{animationDelay:`${i * -0.16}s`}}/>)}{latitudeD.map((d,i)=><path key={`ld-${i}`} d={d} className="mesh-drift mesh-lat" style={{animationDelay:`${i * -0.11}s`}}/>)}</g>
          <g className="energy-ribbons" fill="none" strokeLinecap="round">{wavePaths.map((d,i)=><path key={`wave-${i}`} d={d} stroke={i%2===0?"#55E7FF":"#F45CFF"} strokeOpacity={0.22-i*0.02} strokeWidth={1.3+i*0.18} strokeDasharray="8 18"/>)}</g>
        </g>
        <g className="orb-particle-field">{particles.map((p,i)=><circle key={`particle-${i}`} cx={p.x} cy={p.y} r={p.size} fill={i%3===0?"#62E9FF":i%3===1?"#9E72FF":"#FF5BD9"} opacity={p.opacity} style={{animationDelay:p.delay}}/>)}</g>
        <g className="orb-core-presence"><circle cx="250" cy="252" r="43" fill="rgba(7,6,13,.76)" stroke="rgba(255,255,255,.14)" strokeWidth="1"/><circle cx="250" cy="252" r="30" fill="url(#sabaBlob)" opacity="0.7"/><circle cx="241" cy="242" r="5.5" fill="#fff" opacity="0.94"/><circle cx="241" cy="242" r="15" fill="#74E9FF" opacity="0.12" filter="url(#sabaBlur)"/></g>
        <g className="orb-satellite-rings" fill="none" strokeLinecap="round"><ellipse cx="250" cy="252" rx="177" ry="105" transform="rotate(-12 250 252)" stroke="#53E9FF" strokeOpacity="0.23" strokeWidth="1"/><ellipse cx="250" cy="252" rx="190" ry="115" transform="rotate(22 250 252)" stroke="#D553FF" strokeOpacity="0.18" strokeWidth="1"/><ellipse cx="250" cy="252" rx="206" ry="122" transform="rotate(58 250 252)" stroke="#E7C65A" strokeOpacity="0.13" strokeWidth="1"/></g>
      </svg>
      <div className="orb-state-plaque"><span className="orb-status-dot"/><span className="orb-state" style={{color}}>{LABEL[safeState]}</span></div>
    </div>
  );
}
