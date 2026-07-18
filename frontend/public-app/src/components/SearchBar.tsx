import { Combobox, ComboboxInput, ComboboxOption, ComboboxOptions } from "@headlessui/react";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@palms/shared";
import { useEffect, useId, useState, type FormEvent, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useApiClient } from "@/api/ApiClientProvider";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { cn } from "@/lib/format";

type SearchBarProps = {
  initialQuery?: string;
  autoFocus?: boolean;
  size?: "lg" | "md";
  className?: string;
  onSubmitQuery?: (query: string) => void;
};

export function SearchBar({
  initialQuery = "",
  autoFocus = false,
  size = "lg",
  className,
  onSubmitQuery,
}: SearchBarProps) {
  const client = useApiClient();
  const navigate = useNavigate();
  const inputId = useId();
  const listboxId = useId();
  const [query, setQuery] = useState(initialQuery);
  const debounced = useDebouncedValue(query.trim(), 300);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const suggestionsQuery = useQuery({
    queryKey: queryKeys.public.suggestions(debounced, 8),
    queryFn: ({ signal }) =>
      client.public.suggestDonors({ query: debounced, limit: 8 }, { signal }),
    enabled: debounced.length >= 2,
    staleTime: 30_000,
  });

  const suggestions = suggestionsQuery.data?.items ?? [];

  function submit(value: string) {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    if (onSubmitQuery) {
      onSubmitQuery(trimmed);
      return;
    }
    navigate(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    submit(query);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setQuery("");
    }
  }

  return (
    <form
      role="search"
      onSubmit={handleSubmit}
      className={cn("w-full", className)}
      aria-label="Search palms"
    >
      <label htmlFor={inputId} className="sr-only">
        Search by donor name or palm code
      </label>
      <Combobox
        value={query}
        onChange={(value) => {
          if (typeof value === "string") {
            setQuery(value);
            submit(value);
          }
        }}
        immediate
      >
        <div
          className={cn(
            "flex overflow-hidden rounded-xl bg-white shadow-lg ring-1 ring-sand-200/80 focus-within:ring-2 focus-within:ring-gold-500",
            size === "lg" ? "min-h-14" : "min-h-12",
          )}
        >
          <ComboboxInput
            id={inputId}
            autoFocus={autoFocus}
            displayValue={() => query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            aria-controls={listboxId}
            aria-autocomplete="list"
            placeholder="Donor name or palm code…"
            className={cn(
              "min-w-0 flex-1 bg-transparent px-4 text-sand-900 placeholder:text-sand-800/45 focus:outline-none",
              size === "lg" ? "text-base sm:text-lg" : "text-sm sm:text-base",
            )}
          />
          <button
            type="submit"
            className="shrink-0 bg-palm-700 px-5 text-sm font-semibold text-sand-50 transition hover:bg-palm-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-gold-400"
          >
            Search
          </button>
        </div>

        {debounced.length >= 2 ? (
          <ComboboxOptions
            id={listboxId}
            anchor="bottom start"
            className="z-40 mt-2 max-h-64 w-[min(100vw-2rem,36rem)] overflow-auto rounded-xl bg-white p-1 shadow-xl ring-1 ring-sand-200 [--anchor-gap:6px]"
          >
            {suggestionsQuery.isLoading ? (
              <div className="px-3 py-2 text-sm text-sand-800/70">Looking up donors…</div>
            ) : null}
            {suggestionsQuery.isError ? (
              <div className="px-3 py-2 text-sm text-red-700">
                Could not load suggestions. Try searching anyway.
              </div>
            ) : null}
            {!suggestionsQuery.isLoading &&
            !suggestionsQuery.isError &&
            suggestions.length === 0 ? (
              <div className="px-3 py-2 text-sm text-sand-800/70">
                No donor matches — press Search to look up palms.
              </div>
            ) : null}
            {suggestions.map((donor) => (
              <ComboboxOption
                key={donor.id}
                value={donor.full_name}
                className="cursor-pointer rounded-lg px-3 py-2 text-sm text-sand-900 data-focus:bg-palm-50 data-focus:text-palm-800"
              >
                {donor.full_name}
              </ComboboxOption>
            ))}
          </ComboboxOptions>
        ) : null}
      </Combobox>
    </form>
  );
}
