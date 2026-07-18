import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div
      role="status"
      className="rounded-2xl border border-dashed border-sand-300 bg-white/60 px-6 py-12 text-center"
    >
      <h2 className="font-display text-2xl font-semibold text-palm-800">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-sand-800/80">{description}</p>
      {action ? <div className="mt-6 flex justify-center">{action}</div> : null}
    </div>
  );
}
