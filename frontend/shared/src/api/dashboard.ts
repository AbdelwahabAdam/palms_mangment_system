import {
  ActivitySchema,
  DashboardOverviewSchema,
  PaginatedSchema,
} from "../contracts";
import type { HttpClient } from "../http";
import type { ListQuery, RequestContext } from "./types";

export function createDashboardApi(http: HttpClient) {
  return {
    overview: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/dashboard/overview",
        response: DashboardOverviewSchema,
        signal: context.signal,
      }),
    activity: (
      query: Omit<ListQuery, "query" | "sort" | "order"> = {},
      context: RequestContext = {},
    ) =>
      http.request({
        method: "GET",
        path: "/admin/dashboard/activity",
        params: query,
        response: PaginatedSchema(ActivitySchema),
        signal: context.signal,
      }),
  };
}

export type DashboardApi = ReturnType<typeof createDashboardApi>;
