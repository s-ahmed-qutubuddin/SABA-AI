import { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  readout,
  action,
}: {
  eyebrow: string;
  title: string;
  readout?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex items-end justify-between gap-4 border-b border-panel-border pb-5">
      <div>
        <div className="font-mono text-[10px] tracking-[0.3em] text-signal">{eyebrow}</div>
        <h1 className="mt-1.5 font-display text-2xl text-text">{title}</h1>
      </div>
      <div className="flex items-center gap-4">
        {readout && (
          <div className="font-mono text-[10px] tracking-[0.2em] text-text-dim">{readout}</div>
        )}
        {action}
      </div>
    </div>
  );
}

export function PageShell({ children }: { children: ReactNode }) {
  return <div className="mx-auto flex h-full w-full max-w-3xl flex-col overflow-y-auto px-8 py-10">{children}</div>;
}
