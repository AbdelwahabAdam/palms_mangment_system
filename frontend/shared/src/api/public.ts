import {
  NonEmptyStringSchema,
  PaginatedSchema,
  PublicDonorSuggestionSchema,
  PublicPalmProfileSchema,
  PublicSearchItemSchema,
  ItemsSchema,
} from "../contracts";
import type { HttpClient } from "../http";
import type { ListQuery, RequestContext } from "./types";

export interface PublicSearchQuery extends ListQuery {
  query: string;
}

export interface PublicSuggestQuery {
  query: string;
  limit?: number;
}

export function createPublicApi(http: HttpClient) {
  return {
    search: (query: PublicSearchQuery, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/public/search",
        params: {
          ...query,
          query: NonEmptyStringSchema.max(120).parse(query.query),
        },
        response: PaginatedSchema(PublicSearchItemSchema),
        signal: context.signal,
      }),
    suggestDonors: (query: PublicSuggestQuery, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/public/donors/suggest",
        params: {
          query: NonEmptyStringSchema.max(120).parse(query.query),
          limit: query.limit,
        },
        response: ItemsSchema(PublicDonorSuggestionSchema),
        signal: context.signal,
      }),
    getPalm: (palmCode: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: `/public/palms/${encodeURIComponent(NonEmptyStringSchema.max(80).parse(palmCode))}`,
        response: PublicPalmProfileSchema,
        signal: context.signal,
      }),
  };
}

export type PublicApi = ReturnType<typeof createPublicApi>;
