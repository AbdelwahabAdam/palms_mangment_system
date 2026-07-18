import { isApiError } from "@palms/shared";

export function getErrorMessage(error: unknown, fallback = "Something went wrong."): string {
  if (isApiError(error)) {
    return error.message || fallback;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
