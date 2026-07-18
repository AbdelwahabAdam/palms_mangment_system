import type { PalmsClient } from "@palms/shared";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { ApiClientProvider } from "@/api/ApiClientProvider";
import { AppShell } from "@/components/layout/AppShell";
import { PalmProfilePage } from "@/pages/PalmProfilePage";
import { SearchPage } from "@/pages/SearchPage";

export function createMockClient(
  overrides: Partial<{
    search: PalmsClient["public"]["search"];
    suggestDonors: PalmsClient["public"]["suggestDonors"];
    getPalm: PalmsClient["public"]["getPalm"];
  }> = {},
): PalmsClient {
  return {
    public: {
      search:
        overrides.search ??
        (async () => ({
          items: [],
          pagination: {
            page: 1,
            page_size: 24,
            total: 0,
            total_pages: 0,
          },
        })),
      suggestDonors:
        overrides.suggestDonors ??
        (async () => ({
          items: [],
        })),
      getPalm:
        overrides.getPalm ??
        (async () => {
          throw new Error("getPalm not mocked");
        }),
    },
  } as unknown as PalmsClient;
}

export function renderWithProviders(
  ui: ReactElement,
  options: {
    client?: PalmsClient;
    route?: string;
  } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  const client = options.client ?? createMockClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ApiClientProvider client={client}>
          <MemoryRouter initialEntries={[options.route ?? "/"]}>
            {children}
          </MemoryRouter>
        </ApiClientProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}

export function renderSearchPage(client: PalmsClient, route = "/search?q=Amira") {
  return renderWithProviders(
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/search" element={<SearchPage />} />
        <Route path="/palms/:palmCode" element={<PalmProfilePage />} />
      </Route>
    </Routes>,
    { client, route },
  );
}

export function renderPalmProfile(client: PalmsClient, palmCode: string) {
  return renderWithProviders(
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/palms/:palmCode" element={<PalmProfilePage />} />
        <Route path="/search" element={<SearchPage />} />
      </Route>
    </Routes>,
    { client, route: `/palms/${palmCode}` },
  );
}
