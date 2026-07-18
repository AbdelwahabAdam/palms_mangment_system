import { HealthSchema, MetaSchema } from "../contracts";
import type { HttpClient } from "../http";
import type { RequestContext } from "./types";

export function createMetaApi(http: HttpClient) {
  return {
    health: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/health",
        response: HealthSchema,
        signal: context.signal,
        enveloped: false,
        absolute: true,
      }),
    meta: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/meta",
        response: MetaSchema,
        signal: context.signal,
      }),
  };
}

export type MetaApi = ReturnType<typeof createMetaApi>;
