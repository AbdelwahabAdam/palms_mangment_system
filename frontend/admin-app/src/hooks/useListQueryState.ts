import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

export interface ListState {
  page: number;
  pageSize: number;
  query: string;
  sort?: string;
  order: "asc" | "desc";
  filters: Record<string, string>;
}

export function useListQueryState(defaults?: {
  sort?: string;
  order?: "asc" | "desc";
  pageSize?: number;
  filterKeys?: string[];
}) {
  const [params, setParams] = useSearchParams();
  const filterKeys = defaults?.filterKeys ?? [];

  const state = useMemo<ListState>(() => {
    const filters: Record<string, string> = {};
    for (const key of filterKeys) {
      const value = params.get(key);
      if (value) filters[key] = value;
    }
    return {
      page: Math.max(1, Number(params.get("page") ?? "1") || 1),
      pageSize: Math.max(
        1,
        Number(params.get("page_size") ?? String(defaults?.pageSize ?? 25)) || 25,
      ),
      query: params.get("query") ?? "",
      sort: params.get("sort") ?? defaults?.sort,
      order: (params.get("order") as "asc" | "desc" | null) ?? defaults?.order ?? "asc",
      filters,
    };
  }, [params, defaults?.order, defaults?.pageSize, defaults?.sort, filterKeys]);

  const [searchDraft, setSearchDraft] = useState(state.query);

  const update = useCallback(
    (patch: Partial<ListState> & { filters?: Record<string, string> }) => {
      const next = new URLSearchParams(params);
      const page = patch.page ?? state.page;
      const pageSize = patch.pageSize ?? state.pageSize;
      const query = patch.query ?? state.query;
      const sort = patch.sort ?? state.sort;
      const order = patch.order ?? state.order;
      const filters = patch.filters ?? state.filters;

      next.set("page", String(page));
      next.set("page_size", String(pageSize));
      if (query) next.set("query", query);
      else next.delete("query");
      if (sort) next.set("sort", sort);
      else next.delete("sort");
      next.set("order", order);

      for (const key of filterKeys) {
        const value = filters[key];
        if (value) next.set(key, value);
        else next.delete(key);
      }

      setParams(next, { replace: true });
    },
    [filterKeys, params, setParams, state],
  );

  return {
    state,
    searchDraft,
    setSearchDraft,
    setPage: (page: number) => update({ page }),
    setPageSize: (pageSize: number) => update({ pageSize, page: 1 }),
    setQuery: (query: string) => update({ query, page: 1 }),
    setSort: (sort: string, order: "asc" | "desc") =>
      update({ sort, order, page: 1 }),
    setFilter: (key: string, value: string) =>
      update({
        filters: { ...state.filters, [key]: value },
        page: 1,
      }),
    clearFilters: () => update({ filters: {}, query: "", page: 1 }),
  };
}
