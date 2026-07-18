import {
  DeleteResponseSchema,
  DonorCreateRequestSchema,
  DonorPatchRequestSchema,
  DonorSchema,
  PaginatedSchema,
  PalmSchema,
  UuidSchema,
} from "../contracts";
import type {
  DonorCreateRequest,
  DonorPatchRequest,
} from "../contracts";
import type { HttpClient } from "../http";
import type { ListQuery, RequestContext } from "./types";

export type DonorsListQuery = ListQuery;

export function createDonorsApi(http: HttpClient) {
  return {
    list: (query: DonorsListQuery = {}, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/donors",
        params: query,
        response: PaginatedSchema(DonorSchema),
        signal: context.signal,
      }),
    create: (input: DonorCreateRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/donors",
        data: DonorCreateRequestSchema.parse(input),
        response: DonorSchema,
        signal: context.signal,
      }),
    get: (donorId: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: `/admin/donors/${UuidSchema.parse(donorId)}`,
        response: DonorSchema,
        signal: context.signal,
      }),
    update: (
      donorId: string,
      input: DonorPatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `/admin/donors/${UuidSchema.parse(donorId)}`,
        data: DonorPatchRequestSchema.parse(input),
        response: DonorSchema,
        signal: context.signal,
      }),
    remove: (donorId: string, context: RequestContext = {}) =>
      http.request({
        method: "DELETE",
        path: `/admin/donors/${UuidSchema.parse(donorId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    palms: (
      donorId: string,
      query: Omit<ListQuery, "query"> = {},
      context: RequestContext = {},
    ) =>
      http.request({
        method: "GET",
        path: `/admin/donors/${UuidSchema.parse(donorId)}/palms`,
        params: query,
        response: PaginatedSchema(PalmSchema),
        signal: context.signal,
      }),
  };
}

export type DonorsApi = ReturnType<typeof createDonorsApi>;
