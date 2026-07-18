import axios from "axios";

import { ApiErrorBodySchema } from "./contracts";
import type { ApiErrorBody } from "./contracts";

export type ApiErrorKind =
  | "api"
  | "cancelled"
  | "timeout"
  | "network"
  | "invalid_response";

export interface ApiErrorOptions {
  status: number;
  code: string;
  message: string;
  details?: ApiErrorBody["error"]["details"];
  kind?: ApiErrorKind;
  cause?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: ApiErrorBody["error"]["details"] | undefined;
  readonly kind: ApiErrorKind;

  constructor(options: ApiErrorOptions) {
    super(options.message, { cause: options.cause });
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.details = options.details;
    this.kind = options.kind ?? "api";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function isAuthFailure(error: unknown): error is ApiError {
  return isApiError(error) && error.status === 401;
}

/**
 * Converts every transport, envelope, timeout, cancellation, and API failure
 * into the one error class consumed by TanStack Query callers.
 */
export function normalizeApiError(error: unknown): ApiError {
  if (isApiError(error)) {
    return error;
  }

  if (axios.isCancel(error)) {
    return new ApiError({
      status: 0,
      code: "cancelled",
      message: "The request was cancelled.",
      kind: "cancelled",
      cause: error,
    });
  }

  if (axios.isAxiosError(error)) {
    const body = ApiErrorBodySchema.safeParse(error.response?.data);
    if (body.success) {
      return new ApiError({
        status: error.response?.status ?? 0,
        code: body.data.error.code,
        message: body.data.error.message,
        details: body.data.error.details,
        cause: error,
      });
    }

    if (error.code === "ECONNABORTED" || error.code === "ETIMEDOUT") {
      return new ApiError({
        status: 0,
        code: "timeout",
        message: "The request timed out.",
        kind: "timeout",
        cause: error,
      });
    }

    if (!error.response) {
      return new ApiError({
        status: 0,
        code: "network_error",
        message: "The network request could not be completed.",
        kind: "network",
        cause: error,
      });
    }

    return new ApiError({
      status: error.response.status,
      code: "http_error",
      message: "The request could not be processed.",
      cause: error,
    });
  }

  return new ApiError({
    status: 0,
    code: "unknown_error",
    message: error instanceof Error ? error.message : "An unexpected error occurred.",
    kind: "invalid_response",
    cause: error,
  });
}
