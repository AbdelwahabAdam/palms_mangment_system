import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material";
import { createPalmsClient, type CurrentUser, type PalmsClient } from "@palms/shared";
import { ApiError } from "@palms/shared";

import { ApiClientProvider } from "@/api/ApiClientProvider";
import { theme } from "@/theme";

export function makeUser(
  overrides: Partial<CurrentUser> & { permissions?: string[] } = {},
): CurrentUser {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    email: "admin@example.com",
    full_name: "Admin User",
    is_active: true,
    role: {
      id: "22222222-2222-2222-2222-222222222222",
      name: "Super Admin",
    },
    last_login_at: null,
    avatar_url: null,
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
    permissions: overrides.permissions ?? ["palms.read", "palms.create"],
    two_factor: { enabled: false, mode: "placeholder" },
    ...overrides,
  };
}

export function createMockClient(options?: {
  me?: () => Promise<CurrentUser>;
  login?: (input: { email: string; password: string }) => Promise<{
    user: Omit<CurrentUser, "two_factor">;
  }>;
}): PalmsClient {
  const base = createPalmsClient({
    apiBaseUrl: "/api/v1",
    adapter: async () => {
      throw new ApiError({
        status: 500,
        code: "unexpected",
        message: "Unexpected network call in test.",
      });
    },
  });

  return {
    ...base,
    auth: {
      ...base.auth,
      me: options?.me
        ? async () => options.me!()
        : async () => {
            throw new ApiError({
              status: 401,
              code: "unauthorized",
              message: "Not authenticated.",
            });
          },
      login: options?.login
        ? async (input) => options.login!(input)
        : base.auth.login,
      logout: async () => ({ logged_out: true as const }),
      forgotPassword: base.auth.forgotPassword,
      resetPassword: base.auth.resetPassword,
      changePassword: base.auth.changePassword,
      enableTwoFactor: base.auth.enableTwoFactor,
      disableTwoFactor: base.auth.disableTwoFactor,
    },
  };
}

export function renderWithProviders(
  ui: ReactElement,
  options?: {
    route?: string;
    client?: PalmsClient;
    renderOptions?: Omit<RenderOptions, "wrapper">;
  },
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const client = options?.client ?? createMockClient();
  const route = options?.route ?? "/overview";

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={[route]}>
            <ApiClientProvider client={client}>{children}</ApiClientProvider>
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options?.renderOptions }),
    client,
    queryClient,
  };
}
