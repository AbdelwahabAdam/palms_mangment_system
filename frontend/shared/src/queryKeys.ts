import type { ListQuery } from "./api/types";

export const queryKeys = {
  health: ["health"] as const,
  meta: ["meta"] as const,
  me: ["auth", "me"] as const,
  profile: ["admin", "profile"] as const,
  users: {
    all: ["admin", "users"] as const,
    list: (query: ListQuery = {}) => ["admin", "users", "list", query] as const,
    detail: (userId: string) => ["admin", "users", userId] as const,
    auditLogs: (userId: string, query: ListQuery = {}) =>
      ["admin", "users", userId, "audit-logs", query] as const,
  },
  donors: {
    all: ["admin", "donors"] as const,
    list: (query: ListQuery = {}) => ["admin", "donors", "list", query] as const,
    detail: (donorId: string) => ["admin", "donors", donorId] as const,
    palms: (donorId: string, query: ListQuery = {}) =>
      ["admin", "donors", donorId, "palms", query] as const,
  },
  sections: {
    all: ["admin", "sections"] as const,
    list: (query: ListQuery = {}) =>
      ["admin", "sections", "list", query] as const,
    detail: (sectionId: string) => ["admin", "sections", sectionId] as const,
  },
  palms: {
    all: ["admin", "palms"] as const,
    list: (query: ListQuery = {}) => ["admin", "palms", "list", query] as const,
    detail: (palmId: string) => ["admin", "palms", palmId] as const,
  },
  public: {
    search: (query: ListQuery & { query?: string } = {}) =>
      ["public", "search", query] as const,
    suggestions: (query: string, limit?: number) =>
      ["public", "donors", "suggest", query, limit] as const,
    palm: (palmCode: string) => ["public", "palms", palmCode] as const,
  },
  dashboard: {
    overview: ["admin", "dashboard", "overview"] as const,
    activity: (query: ListQuery = {}) =>
      ["admin", "dashboard", "activity", query] as const,
  },
  reports: {
    types: ["admin", "reports", "types"] as const,
    templates: ["admin", "reports", "templates"] as const,
    schedules: ["admin", "report-schedules"] as const,
    schedule: (scheduleId: string) =>
      ["admin", "report-schedules", scheduleId] as const,
    scheduleRuns: (scheduleId: string, query: ListQuery = {}) =>
      ["admin", "report-schedules", scheduleId, "runs", query] as const,
  },
} as const;
