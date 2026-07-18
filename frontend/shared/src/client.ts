import type { AxiosAdapter } from "axios";

import { createAuthApi } from "./api/auth";
import { createDashboardApi } from "./api/dashboard";
import { createDonorsApi } from "./api/donors";
import { createMetaApi } from "./api/meta";
import { createPalmsApi } from "./api/palms";
import { createProfileApi } from "./api/profile";
import { createPublicApi } from "./api/public";
import { createReportsApi } from "./api/reports";
import { createSectionsApi } from "./api/sections";
import { createUsersApi } from "./api/users";
import { resolveRuntimeConfig } from "./config";
import type { RuntimeEnv } from "./config";
import type { ApiError } from "./errors";
import { createHttpClient } from "./http";
import type { HttpClient } from "./http";
import { defaultFormDataFactory } from "./multipart";
import type { FormDataFactory } from "./multipart";

export interface CreatePalmsClientOptions {
  env?: RuntimeEnv;
  apiBaseUrl?: string;
  timeoutMs?: number;
  adapter?: AxiosAdapter;
  onAuthFailure?: (error: ApiError) => void;
  createFormData?: FormDataFactory;
}

export interface PalmsClient {
  readonly http: HttpClient;
  readonly meta: ReturnType<typeof createMetaApi>;
  readonly auth: ReturnType<typeof createAuthApi>;
  readonly profile: ReturnType<typeof createProfileApi>;
  readonly users: ReturnType<typeof createUsersApi>;
  readonly donors: ReturnType<typeof createDonorsApi>;
  readonly sections: ReturnType<typeof createSectionsApi>;
  readonly palms: ReturnType<typeof createPalmsApi>;
  readonly public: ReturnType<typeof createPublicApi>;
  readonly dashboard: ReturnType<typeof createDashboardApi>;
  readonly reports: ReturnType<typeof createReportsApi>;
}

/**
 * Builds a fully typed API client for public and admin applications.
 * All runtime configuration is injected; nothing is read from globals.
 */
export function createPalmsClient(
  options: CreatePalmsClientOptions = {},
): PalmsClient {
  const runtime = resolveRuntimeConfig(options.env ?? {});
  const http = createHttpClient({
    baseUrl: options.apiBaseUrl ?? runtime.apiBaseUrl,
    timeoutMs: options.timeoutMs ?? runtime.timeoutMs,
    adapter: options.adapter,
    onAuthFailure: options.onAuthFailure,
  });
  const createFormData = options.createFormData ?? defaultFormDataFactory;

  return {
    http,
    meta: createMetaApi(http),
    auth: createAuthApi(http),
    profile: createProfileApi(http, createFormData),
    users: createUsersApi(http),
    donors: createDonorsApi(http),
    sections: createSectionsApi(http, createFormData),
    palms: createPalmsApi(http, createFormData),
    public: createPublicApi(http),
    dashboard: createDashboardApi(http),
    reports: createReportsApi(http),
  };
}
