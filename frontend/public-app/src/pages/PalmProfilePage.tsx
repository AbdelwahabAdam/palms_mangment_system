import { isApiError, queryKeys } from "@palms/shared";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useApiClient } from "@/api/ApiClientProvider";
import { ChildrenPalmsList } from "@/components/ChildrenPalmsList";
import { DiseaseHistoryTimeline } from "@/components/DiseaseHistoryTimeline";
import { DonorInfoCard } from "@/components/DonorInfoCard";
import { EmptyState } from "@/components/EmptyState";
import { HarvestSummaryCard } from "@/components/HarvestSummaryCard";
import { ProfileSkeleton } from "@/components/LoadingSkeleton";
import { PalmImageGallery } from "@/components/PalmImageGallery";
import { PalmInfoCard } from "@/components/PalmInfoCard";
import { SectionMap } from "@/components/SectionMap";
import { formatAge } from "@/lib/format";

export function PalmProfilePage() {
  const { palmCode = "" } = useParams();
  const client = useApiClient();

  const profileQuery = useQuery({
    queryKey: queryKeys.public.palm(palmCode),
    queryFn: ({ signal }) => client.public.getPalm(palmCode, { signal }),
    enabled: palmCode.length > 0,
  });

  if (!palmCode) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <EmptyState
          title="Missing palm code"
          description="Choose a palm from search results to view its profile."
          action={
            <Link
              to="/search"
              className="rounded-lg bg-palm-700 px-4 py-2 text-sm font-semibold text-sand-50"
            >
              Go to search
            </Link>
          }
        />
      </div>
    );
  }

  if (profileQuery.isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <ProfileSkeleton />
      </div>
    );
  }

  if (profileQuery.isError || !profileQuery.data) {
    const notFound = isApiError(profileQuery.error) && profileQuery.error.status === 404;
    return (
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <EmptyState
          title={notFound ? "Palm not found" : "Could not load palm"}
          description={
            isApiError(profileQuery.error)
              ? profileQuery.error.message
              : "Please try again in a moment."
          }
          action={
            <div className="flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={() => void profileQuery.refetch()}
                className="rounded-lg bg-palm-700 px-4 py-2 text-sm font-semibold text-sand-50 hover:bg-palm-600"
              >
                Retry
              </button>
              <Link
                to="/search"
                className="rounded-lg bg-sand-100 px-4 py-2 text-sm font-semibold text-palm-800 ring-1 ring-sand-200"
              >
                Back to search
              </Link>
            </div>
          }
        />
      </div>
    );
  }

  const palm = profileQuery.data;

  return (
    <article className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-sand-800/70">
        <Link to="/search" className="hover:text-palm-700 hover:underline">
          Search
        </Link>
        <span aria-hidden className="mx-2">
          /
        </span>
        <span className="text-sand-900">{palm.code}</span>
      </nav>

      <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-gold-600">
            Palm profile
          </p>
          <h1 className="mt-1 font-display text-4xl font-semibold text-palm-800 sm:text-5xl">
            {palm.code}
          </h1>
          <p className="mt-2 text-sand-800/80">
            {formatAge(palm.current_age)}
            {palm.current_health_status
              ? ` · ${palm.current_health_status}`
              : null}
          </p>
        </div>
      </header>

      <div className="mt-8">
        <PalmImageGallery images={palm.images} palmCode={palm.code} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <PalmInfoCard palm={palm} />
          <HarvestSummaryCard
            totalAmount={palm.harvest_summary.total_amount}
            totalRevenue={palm.harvest_summary.total_revenue}
            recordsCount={palm.harvest_summary.records_count}
          />
          <DiseaseHistoryTimeline diseases={palm.diseases} />
          <ChildrenPalmsList childrenPalms={palm.children} />
        </div>
        <aside className="space-y-6">
          <DonorInfoCard donorName={palm.donor.full_name} />
          <SectionMap
            name={palm.section.name}
            locationName={palm.section.location_name}
            imageUrl={palm.section.image_url}
          />
        </aside>
      </div>
    </article>
  );
}
