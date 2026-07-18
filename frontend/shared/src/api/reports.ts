import {
  DeleteResponseSchema,
  ItemsSchema,
  PaginatedSchema,
  ReportGenerateRequestSchema,
  ReportPreviewRequestSchema,
  ReportPreviewResponseSchema,
  ReportRunDownloadSchema,
  ReportRunSchema,
  ReportScheduleCreateRequestSchema,
  ReportSchedulePatchRequestSchema,
  ReportScheduleSchema,
  ReportTemplateCreateRequestSchema,
  ReportTemplateSchema,
  ReportTypeSchema,
  UuidSchema,
} from "../contracts";
import type {
  ReportGenerateRequest,
  ReportPreviewRequest,
  ReportScheduleCreateRequest,
  ReportSchedulePatchRequest,
  ReportTemplateCreateRequest,
} from "../contracts";
import type { HttpClient } from "../http";
import type { ListQuery, RequestContext } from "./types";

export function createReportsApi(http: HttpClient) {
  return {
    types: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/reports/types",
        response: ItemsSchema(ReportTypeSchema),
        signal: context.signal,
      }),
    preview: (input: ReportPreviewRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/reports/preview",
        data: ReportPreviewRequestSchema.parse(input),
        response: ReportPreviewResponseSchema,
        signal: context.signal,
      }),
    generate: (input: ReportGenerateRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/reports/generate",
        data: ReportGenerateRequestSchema.parse(input),
        response: ReportRunSchema,
        signal: context.signal,
      }),
    listTemplates: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/reports/templates",
        response: ItemsSchema(ReportTemplateSchema),
        signal: context.signal,
      }),
    createTemplate: (
      input: ReportTemplateCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/admin/reports/templates",
        data: ReportTemplateCreateRequestSchema.parse(input),
        response: ReportTemplateSchema,
        signal: context.signal,
      }),
    listSchedules: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/report-schedules",
        response: ItemsSchema(ReportScheduleSchema),
        signal: context.signal,
      }),
    createSchedule: (
      input: ReportScheduleCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/admin/report-schedules",
        data: ReportScheduleCreateRequestSchema.parse(input),
        response: ReportScheduleSchema,
        signal: context.signal,
      }),
    getSchedule: (scheduleId: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: `/admin/report-schedules/${UuidSchema.parse(scheduleId)}`,
        response: ReportScheduleSchema,
        signal: context.signal,
      }),
    updateSchedule: (
      scheduleId: string,
      input: ReportSchedulePatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `/admin/report-schedules/${UuidSchema.parse(scheduleId)}`,
        data: ReportSchedulePatchRequestSchema.parse(input),
        response: ReportScheduleSchema,
        signal: context.signal,
      }),
    removeSchedule: (scheduleId: string, context: RequestContext = {}) =>
      http.request({
        method: "DELETE",
        path: `/admin/report-schedules/${UuidSchema.parse(scheduleId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    pauseSchedule: (scheduleId: string, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: `/admin/report-schedules/${UuidSchema.parse(scheduleId)}/pause`,
        response: ReportScheduleSchema,
        signal: context.signal,
      }),
    resumeSchedule: (scheduleId: string, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: `/admin/report-schedules/${UuidSchema.parse(scheduleId)}/resume`,
        response: ReportScheduleSchema,
        signal: context.signal,
      }),
    listScheduleRuns: (
      scheduleId: string,
      query: Omit<ListQuery, "query" | "sort" | "order"> = {},
      context: RequestContext = {},
    ) =>
      http.request({
        method: "GET",
        path: `/admin/report-schedules/${UuidSchema.parse(scheduleId)}/runs`,
        params: query,
        response: PaginatedSchema(ReportRunSchema),
        signal: context.signal,
      }),
    downloadRun: (runId: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: `/admin/report-runs/${UuidSchema.parse(runId)}/download`,
        response: ReportRunDownloadSchema,
        signal: context.signal,
      }),
  };
}

export type ReportsApi = ReturnType<typeof createReportsApi>;
