import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0A0D12",
        "ink-deep": "#050709",
        panel: "#12161D",
        "panel-2": "#171C26",
        "panel-border": "rgba(255,255,255,0.06)",
        signal: "var(--accent)",
        "signal-dim": "color-mix(in srgb, var(--accent) 34%, #10131a)",
        violet: "var(--accent-tertiary)",
        "violet-dim": "color-mix(in srgb, var(--accent-tertiary) 34%, #10131a)",
        warn: "var(--accent-warm)",
        text: "#E7EBF0",
        "text-dim": "#8891A0",
      },
      fontFamily: {
        display: ["'Cinzel'", "serif"],
        body: ["'Manrope'", "sans-serif"],
        mono: ["'DM Mono'", "monospace"],
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.35)",
        "glow-signal": "0 0 46px -8px color-mix(in srgb, var(--accent) 42%, transparent)",
        "glow-violet": "0 0 46px -8px color-mix(in srgb, var(--accent-tertiary) 34%, transparent)",
      },
      backgroundImage: {
        "grain": "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.035) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
} satisfies Config;
