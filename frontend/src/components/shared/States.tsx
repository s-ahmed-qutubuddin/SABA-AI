import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-1 items-center justify-center py-16">
      <div className="flex items-center gap-3 font-mono text-xs tracking-[0.2em] text-text-dim">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal shadow-[0_0_8px_2px_color-mix(in srgb, var(--accent) 50%, transparent)]" />
        {label.toUpperCase()}
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="glass-card flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl py-16 text-center">
      <div className="font-mono text-xs tracking-[0.2em] text-warn">SOMETHING WENT WRONG</div>
      <div className="max-w-sm text-sm text-text-dim">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded-full border border-panel-border px-4 py-1.5 text-xs text-text transition hover:border-signal/40 hover:text-signal"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  hint,
  action,
}: {
  icon: LucideIcon;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-panel-border py-16 text-center">
      <Icon size={26} strokeWidth={1.25} className="text-signal/70" />
      <div className="font-display text-sm text-text">{title}</div>
      {hint && <div className="max-w-xs text-xs text-text-dim">{hint}</div>}
      {action}
    </div>
  );
}
