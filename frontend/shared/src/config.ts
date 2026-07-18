export interface RuntimeConfig {
  apiBaseUrl: string;
  timeoutMs: number;
}

export interface RuntimeEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_TIMEOUT_MS?: string;
}

const DEFAULT_API_BASE_URL = "/api/v1";
const DEFAULT_TIMEOUT_MS = 15_000;

function normalizeBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/+$/, "");
  if (!normalized) {
    throw new Error("VITE_API_BASE_URL must not be empty.");
  }
  return normalized;
}

function parseTimeout(value: string | undefined): number {
  if (value === undefined || value.trim() === "") {
    return DEFAULT_TIMEOUT_MS;
  }

  const timeout = Number(value);
  if (!Number.isSafeInteger(timeout) || timeout <= 0) {
    throw new Error("VITE_API_TIMEOUT_MS must be a positive integer.");
  }
  return timeout;
}

/**
 * Creates runtime configuration from an explicitly supplied Vite env object.
 * Apps should pass `import.meta.env`; the shared package never reads globals.
 */
export function resolveRuntimeConfig(env: RuntimeEnv = {}): RuntimeConfig {
  return {
    apiBaseUrl: normalizeBaseUrl(env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL),
    timeoutMs: parseTimeout(env.VITE_API_TIMEOUT_MS),
  };
}
