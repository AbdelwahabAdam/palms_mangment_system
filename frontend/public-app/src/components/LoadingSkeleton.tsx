import { cn } from "@/lib/format";

export function LoadingSkeleton({
  className,
  lines = 3,
}: {
  className?: string;
  lines?: number;
}) {
  return (
    <div
      className={cn("animate-pulse space-y-3", className)}
      role="status"
      aria-live="polite"
      aria-label="Loading"
    >
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className={cn(
            "rounded-xl bg-sand-200/80",
            index === 0 ? "h-40" : "h-4",
            index === 1 ? "w-3/4" : index === 2 ? "w-1/2" : "w-full",
          )}
        />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function SearchResultsSkeleton() {
  return (
    <ul className="space-y-4" aria-busy="true" aria-label="Loading search results">
      {Array.from({ length: 4 }, (_, index) => (
        <li
          key={index}
          className="flex animate-pulse flex-col overflow-hidden rounded-2xl bg-white/80 ring-1 ring-sand-200/70 sm:flex-row"
        >
          <div className="h-32 w-full bg-sand-200/80 sm:h-auto sm:w-40" />
          <div className="flex flex-1 flex-col gap-3 p-5">
            <div className="h-5 w-32 rounded bg-sand-200/80" />
            <div className="h-4 w-48 rounded bg-sand-200/70" />
            <div className="h-4 w-40 rounded bg-sand-200/60" />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ProfileSkeleton() {
  return (
    <div className="animate-pulse space-y-6" aria-busy="true" aria-label="Loading palm profile">
      <div className="h-10 w-48 rounded bg-sand-200/80" />
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="aspect-[4/3] rounded-2xl bg-sand-200/80 sm:col-span-2 sm:row-span-2 sm:aspect-auto sm:min-h-72" />
        <div className="aspect-[4/3] rounded-2xl bg-sand-200/70" />
        <div className="aspect-[4/3] rounded-2xl bg-sand-200/70" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-40 rounded-2xl bg-sand-200/70" />
        <div className="h-40 rounded-2xl bg-sand-200/70" />
      </div>
    </div>
  );
}
