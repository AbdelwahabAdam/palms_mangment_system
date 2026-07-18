import type { PublicPalmProfile } from "@palms/shared";

import { formatDate } from "@/lib/format";

type Disease = PublicPalmProfile["diseases"][number];

type DiseaseHistoryTimelineProps = {
  diseases: Disease[];
};

export function DiseaseHistoryTimeline({ diseases }: DiseaseHistoryTimelineProps) {
  return (
    <section
      aria-labelledby="disease-heading"
      className="rounded-2xl bg-white/90 p-5 shadow-sm ring-1 ring-sand-200/80 sm:p-6"
    >
      <h2 id="disease-heading" className="font-display text-xl font-semibold text-palm-800">
        Disease timeline
      </h2>
      {diseases.length === 0 ? (
        <p className="mt-4 text-sm text-sand-800/75">No disease records on file.</p>
      ) : (
        <ol className="relative mt-6 space-y-6 border-l border-sand-300 pl-6">
          {diseases.map((disease) => (
            <li key={`${disease.disease_name}-${disease.detected_at}`} className="relative">
              <span
                aria-hidden
                className="absolute -left-[1.625rem] top-1.5 h-3 w-3 rounded-full bg-gold-500 ring-4 ring-sand-50"
              />
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h3 className="font-semibold text-sand-900">{disease.disease_name}</h3>
                <time dateTime={disease.detected_at} className="text-sm text-sand-800/65">
                  Detected {formatDate(disease.detected_at)}
                </time>
                <span className="rounded-full bg-sand-100 px-2 py-0.5 text-xs font-medium capitalize text-palm-800">
                  {disease.status}
                </span>
              </div>
              {disease.notes ? (
                <p className="mt-2 text-sm text-sand-800/80">{disease.notes}</p>
              ) : null}
              {disease.treatments.length > 0 ? (
                <ul className="mt-3 space-y-2 border-t border-sand-200/70 pt-3">
                  {disease.treatments.map((treatment) => (
                    <li
                      key={`${treatment.treatment_name}-${treatment.treatment_date}`}
                      className="text-sm text-sand-800"
                    >
                      <span className="font-medium">{treatment.treatment_name}</span>
                      <span className="text-sand-800/60">
                        {" "}
                        · {formatDate(treatment.treatment_date)}
                      </span>
                      {treatment.notes ? (
                        <p className="mt-0.5 text-sand-800/75">{treatment.notes}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
