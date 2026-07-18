import { isApiError, queryKeys } from "@palms/shared";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { useApiClient } from "@/api/ApiClientProvider";
import { EmptyState } from "@/components/EmptyState";
import { SearchResultsSkeleton } from "@/components/LoadingSkeleton";
import { PalmResultCard } from "@/components/PalmResultCard";
import { SearchBar } from "@/components/SearchBar";

export function SearchPage() {
  const client = useApiClient();
  const [params, setParams] = useSearchParams();
  const query = (params.get("q") ?? "").trim();

  const searchQuery = useQuery({
    queryKey: queryKeys.public.search({ query, page: 1, page_size: 24 }),
    queryFn: ({ signal }) =>
      client.public.search({ query, page: 1, page_size: 24 }, { signal }),
    enabled: query.length > 0,
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-gold-600">
          Discover
        </p>
        <h1 className="mt-2 font-display text-3xl font-semibold text-palm-800 sm:text-4xl">
          Search palms
        </h1>
        <p className="mt-3 text-sand-800/80">
          Look up palms by donor name or palm code. Results update as you search.
        </p>
      </header>

      <div className="mt-8 max-w-2xl">
        <SearchBar
          initialQuery={query}
          onSubmitQuery={(next) => {
            setParams(next ? { q: next } : {});
          }}
        />
      </div>

      <div className="mt-10">
        {!query ? (
          <EmptyState
            title="Start with a name or code"
            description="Enter a donor name or palm code above to see matching Lifemaker palms."
          />
        ) : null}

        {query && searchQuery.isLoading ? <SearchResultsSkeleton /> : null}

        {query && searchQuery.isError ? (
          <EmptyState
            title="Search unavailable"
            description={
              isApiError(searchQuery.error)
                ? searchQuery.error.message
                : "Something went wrong while searching. Please try again."
            }
            action={
              <button
                type="button"
                onClick={() => void searchQuery.refetch()}
                className="rounded-lg bg-palm-700 px-4 py-2 text-sm font-semibold text-sand-50 hover:bg-palm-600"
              >
                Retry
              </button>
            }
          />
        ) : null}

        {query && searchQuery.isSuccess && searchQuery.data.items.length === 0 ? (
          <EmptyState
            title="No palms found"
            description={`Nothing matched “${query}”. Try another donor name or palm code.`}
            action={
              <Link
                to="/"
                className="rounded-lg bg-palm-700 px-4 py-2 text-sm font-semibold text-sand-50 hover:bg-palm-600"
              >
                Back to home
              </Link>
            }
          />
        ) : null}

        {query && searchQuery.isSuccess && searchQuery.data.items.length > 0 ? (
          <div>
            <p className="mb-4 text-sm text-sand-800/70" role="status">
              {searchQuery.data.pagination.total} result
              {searchQuery.data.pagination.total === 1 ? "" : "s"}
            </p>
            <ul className="space-y-4">
              {searchQuery.data.items.map((item, index) => (
                <li key={item.palm_id}>
                  <PalmResultCard item={item} index={index} />
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
