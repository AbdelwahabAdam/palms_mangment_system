import axios from "axios";
import type { AxiosAdapter, AxiosInstance, Method } from "axios";
import type { z } from "zod";

import { ApiError, normalizeApiError } from "./errors";
import { serializeParams } from "./params";
import type { QueryParams } from "./params";

export interface HttpClientOptions {
  baseUrl: string;
  timeoutMs: number;
  adapter?: AxiosAdapter;
  onAuthFailure?: (error: ApiError) => void;
}

export interface RequestOptions<Schema extends z.ZodTypeAny> {
  method: Method;
  path: string;
  response: Schema;
  data?: unknown;
  params?: QueryParams;
  signal?: AbortSignal;
  headers?: Readonly<Record<string, string>>;
  enveloped?: boolean;
  /** When true, ignore the API version base URL (used for /health). */
  absolute?: boolean;
}

export interface HttpClient {
  readonly instance: AxiosInstance;
  request<Schema extends z.ZodTypeAny>(
    options: RequestOptions<Schema>,
  ): Promise<z.infer<Schema>>;
  createAbortController(): AbortController;
}

function assertPath(path: string): void {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new TypeError(
      "API paths must be absolute paths relative to the API base URL.",
    );
  }
}

function originFromApiBase(apiBaseUrl: string): string {
  const trimmed = apiBaseUrl.replace(/\/+$/, "");
  if (trimmed.endsWith("/api/v1")) {
    const origin = trimmed.slice(0, -"/api/v1".length);
    return origin === "" ? "" : origin;
  }
  return "";
}

/**
 * Creates an isolated Axios client. It never reads `window`, storage, or env;
 * tests can provide an Axios adapter and applications inject runtime settings.
 */
export function createHttpClient(options: HttpClientOptions): HttpClient {
  const instance = axios.create({
    baseURL: options.baseUrl,
    timeout: options.timeoutMs,
    withCredentials: true,
    adapter: options.adapter,
    paramsSerializer: { serialize: serializeParams },
  });

  instance.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      const normalized = normalizeApiError(error);
      if (normalized.status === 401 && normalized.code === "unauthorized") {
        options.onAuthFailure?.(normalized);
      }
      return Promise.reject(normalized);
    },
  );

  return {
    instance,
    createAbortController(): AbortController {
      if (typeof AbortController === "undefined") {
        throw new ApiError({
          status: 0,
          code: "cancellation_unavailable",
          message: "AbortController is unavailable in this runtime.",
          kind: "invalid_response",
        });
      }
      return new AbortController();
    },
    async request<Schema extends z.ZodTypeAny>(
      request: RequestOptions<Schema>,
    ): Promise<z.infer<Schema>> {
      assertPath(request.path);
      const multipart =
        typeof FormData !== "undefined" && request.data instanceof FormData
          ? true
          : Boolean(
              request.data &&
                typeof (request.data as { append?: unknown }).append ===
                  "function",
            );
      try {
        const response = await instance.request<unknown>({
          method: request.method,
          url: request.absolute
            ? `${originFromApiBase(options.baseUrl)}${request.path}`
            : request.path,
          baseURL: request.absolute ? undefined : options.baseUrl,
          data: request.data,
          params: request.params,
          signal: request.signal,
          headers: multipart
            ? { ...request.headers, "Content-Type": undefined }
            : request.headers,
          transformRequest: multipart ? [(data) => data] : undefined,
        });

        if (request.enveloped === false) {
          const parsed = request.response.safeParse(response.data);
          if (parsed.success) {
            return parsed.data as z.infer<Schema>;
          }
          throw new ApiError({
            status: response.status,
            code: "invalid_response",
            message: "The server returned an invalid response body.",
            kind: "invalid_response",
            cause: parsed.error,
          });
        }

        if (
          response.data === null ||
          typeof response.data !== "object" ||
          !("data" in response.data)
        ) {
          throw new ApiError({
            status: response.status,
            code: "invalid_response",
            message: "The server returned an invalid API envelope.",
            kind: "invalid_response",
          });
        }

        const parsed = request.response.safeParse(
          (response.data as { data: unknown }).data,
        );
        if (parsed.success) {
          return parsed.data as z.infer<Schema>;
        }
        throw new ApiError({
          status: response.status,
          code: "invalid_response",
          message: "The server returned an invalid API envelope.",
          kind: "invalid_response",
          cause: parsed.error,
        });
      } catch (error: unknown) {
        throw normalizeApiError(error);
      }
    },
  };
}
