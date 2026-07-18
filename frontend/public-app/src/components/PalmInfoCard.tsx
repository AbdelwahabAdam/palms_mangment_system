import type { PublicPalmProfile } from "@palms/shared";

import { formatAge, formatDate } from "@/lib/format";

type PalmInfoCardProps = {
  palm: PublicPalmProfile;
};

export function PalmInfoCard({ palm }: PalmInfoCardProps) {
  return (
    <section
      aria-labelledby="palm-info-heading"
      className="rounded-2xl bg-white/90 p-5 shadow-sm ring-1 ring-sand-200/80 sm:p-6"
    >
      <h2 id="palm-info-heading" className="font-display text-xl font-semibold text-palm-800">
        Palm details
      </h2>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-sand-800/60">Code</dt>
          <dd className="font-medium text-sand-900">{palm.code}</dd>
        </div>
        <div>
          <dt className="text-sand-800/60">Age</dt>
          <dd className="font-medium text-sand-900">{formatAge(palm.current_age)}</dd>
        </div>
        <div>
          <dt className="text-sand-800/60">Status</dt>
          <dd className="font-medium capitalize text-sand-900">{palm.status}</dd>
        </div>
        <div>
          <dt className="text-sand-800/60">Health</dt>
          <dd className="font-medium capitalize text-sand-900">
            {palm.current_health_status ?? "—"}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-sand-800/60">Planted</dt>
          <dd className="font-medium text-sand-900">
            {formatDate(palm.plantation_date)}
          </dd>
        </div>
        {palm.description ? (
          <div className="sm:col-span-2">
            <dt className="text-sand-800/60">Notes</dt>
            <dd className="mt-1 text-sand-900">{palm.description}</dd>
          </div>
        ) : null}
      </dl>
    </section>
  );
}
