import axios from "axios";
import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import { describe, expect, it, vi } from "vitest";

import { createPalmsClient } from "./client";
import { ApiError, normalizeApiError } from "./errors";
import { serializeParams } from "./params";
import { createMultipartBody } from "./multipart";
import { openReportDownloads } from "./downloads";
import { resolveRuntimeConfig } from "./config";

function createAdapter(
  handler: (config: InternalAxiosRequestConfig) =>
    | {
        status: number;
        data: unknown;
        headers?: Record<string, string>;
      }
    | Promise<{
        status: number;
        data: unknown;
        headers?: Record<string, string>;
      }>,
): AxiosAdapter {
  return async (config) => {
    const result = await handler(config);
    if (result.status >= 400) {
      throw new axios.AxiosError(
        "Request failed",
        "ERR_BAD_REQUEST",
        config,
        {},
        {
          data: result.data,
          status: result.status,
          statusText: String(result.status),
          headers: result.headers ?? {},
          config,
        },
      );
    }
    return {
      data: result.data,
      status: result.status,
      statusText: String(result.status),
      headers: result.headers ?? {},
      config,
      request: {},
    };
  };
}

function requestBody(config: InternalAxiosRequestConfig): unknown {
  if (typeof config.data === "string") {
    return JSON.parse(config.data) as unknown;
  }
  return config.data;
}

describe("serializeParams", () => {
  it("serializes scalars and repeated array keys", () => {
    expect(
      serializeParams({
        page: 2,
        active: true,
        tags: ["a", "b"],
        empty: null,
        missing: undefined,
      }),
    ).toBe("page=2&active=true&tags=a&tags=b");
  });
});

describe("resolveRuntimeConfig", () => {
  it("defaults to the versioned API base", () => {
    expect(resolveRuntimeConfig()).toEqual({
      apiBaseUrl: "/api/v1",
      timeoutMs: 15_000,
    });
  });
});

describe("createPalmsClient", () => {
  it("unwraps success envelopes and posts login payloads", async () => {
    const adapter = createAdapter((config) => {
      expect(config.method?.toLowerCase()).toBe("post");
      expect(config.url).toBe("/auth/login");
      expect(requestBody(config)).toEqual({
        email: "admin@example.com",
        password: "StrongPassword123",
      });
      return {
        status: 200,
        data: {
          data: {
            user: {
              id: "11111111-1111-4111-8111-111111111111",
              email: "admin@example.com",
              full_name: "Admin",
              is_active: true,
              role: {
                id: "22222222-2222-4222-8222-222222222222",
                name: "Super Admin",
              },
              last_login_at: null,
              avatar_url: null,
              created_at: "2026-01-01T00:00:00",
              updated_at: "2026-01-01T00:00:00",
              permissions: ["users.read"],
            },
          },
        },
      };
    });

    const client = createPalmsClient({ adapter });
    const result = await client.auth.login({
      email: "admin@example.com",
      password: "StrongPassword123",
    });
    expect(result.user.email).toBe("admin@example.com");
    expect(result.user.permissions).toContain("users.read");
  });

  it("normalizes unauthorized auth failures", async () => {
    const onAuthFailure = vi.fn();
    const adapter = createAdapter(() => ({
      status: 401,
      data: {
        error: {
          code: "unauthorized",
          message: "Authentication is required.",
        },
      },
    }));

    const client = createPalmsClient({ adapter, onAuthFailure });
    await expect(client.auth.me()).rejects.toMatchObject({
      status: 401,
      code: "unauthorized",
      kind: "api",
    });
    expect(onAuthFailure).toHaveBeenCalledOnce();
  });

  it("requests absolute health and versioned meta paths", async () => {
    const paths: string[] = [];
    const adapter = createAdapter((config) => {
      paths.push(`${config.baseURL ?? ""}${config.url ?? ""}`);
      if ((config.url ?? "").endsWith("/health") || config.url === "/health") {
        return {
          status: 200,
          data: { status: "ok", database: "ok", version: "0.1.0" },
        };
      }
      return {
        status: 200,
        data: {
          data: {
            service: "palms-api",
            version: "0.1.0",
            api_version: "v1",
          },
        },
      };
    });

    const client = createPalmsClient({
      adapter,
      apiBaseUrl: "http://localhost:8000/api/v1",
    });
    await client.meta.health();
    await client.meta.meta();
    expect(paths[0]).toContain("/health");
    expect(paths[1]).toContain("/meta");
  });

  it("builds multipart uploads for palm images", async () => {
    class FakeFormData {
      readonly entries: Array<[string, unknown, string?]> = [];
      append(name: string, value: unknown, filename?: string) {
        this.entries.push([name, value, filename]);
      }
    }

    const form = new FakeFormData();
    const adapter = createAdapter((config) => {
      expect(config.method?.toLowerCase()).toBe("post");
      expect(config.url).toBe(
        "/admin/palms/33333333-3333-4333-8333-333333333333/images",
      );
      expect(config.data).toBe(form);
      return {
        status: 201,
        data: {
          data: {
            id: "44444444-4444-4444-8444-444444444444",
            thumbnail_url: "http://example/t.jpg",
            medium_url: "http://example/m.jpg",
            full_url: "http://example/f.jpg",
            webp_url: "http://example/f.webp",
            uploaded_at: "2026-01-01T00:00:00",
          },
        },
      };
    });

    const client = createPalmsClient({
      adapter,
      createFormData: () => form as unknown as FormData,
    });
    const blob = new Blob(["fake"], { type: "image/png" });
    const image = await client.palms.uploadImage(
      "33333333-3333-4333-8333-333333333333",
      { file: blob, filename: "palm.png" },
    );
    expect(image.full_url).toContain("f.jpg");
    expect(form.entries[0]?.[0]).toBe("file");
    expect(form.entries[0]?.[2]).toBe("palm.png");
  });

  it("uses public search URL contracts", async () => {
    const adapter = createAdapter((config) => {
      expect(config.method?.toLowerCase()).toBe("get");
      expect(config.url).toBe("/public/search");
      expect(config.params).toMatchObject({ query: "Ahmed" });
      return {
        status: 200,
        data: {
          data: {
            items: [],
            pagination: {
              page: 1,
              page_size: 20,
              total: 0,
              total_pages: 0,
            },
          },
        },
      };
    });

    const client = createPalmsClient({ adapter });
    const result = await client.public.search({ query: "Ahmed" });
    expect(result.items).toEqual([]);
  });
});

describe("normalizeApiError", () => {
  it("wraps unknown errors", () => {
    const error = normalizeApiError(new Error("boom"));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("unknown_error");
  });
});

describe("multipart and downloads", () => {
  it("creates multipart bodies without forcing content-type", () => {
    class FakeFormData {
      readonly entries: Array<[string, unknown, string?]> = [];
      append(name: string, value: unknown, filename?: string) {
        this.entries.push([name, value, filename]);
      }
    }
    const form = new FakeFormData();
    const body = createMultipartBody(
      { file: new Blob(["x"]), filename: "a.png", field: "image" },
      () => form as unknown as FormData,
    );
    expect(body).toBe(form);
    expect(form.entries[0]).toEqual(["image", expect.anything(), "a.png"]);
  });

  it("opens report download URLs through an injected opener", () => {
    const openUrl = vi.fn();
    openReportDownloads(
      [{ filename: "report.csv", download_url: "https://example/report.csv" }],
      openUrl,
    );
    expect(openUrl).toHaveBeenCalledWith("https://example/report.csv");
  });
});
