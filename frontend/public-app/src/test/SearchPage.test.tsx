import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createMockClient, renderSearchPage } from "@/test/test-utils";

describe("SearchPage", () => {
  it("shows results and navigates to a palm profile from a result card", async () => {
    const user = userEvent.setup();
    const search = vi.fn(async () => ({
      items: [
        {
          palm_id: "11111111-1111-4111-8111-111111111111",
          palm_code: "PALM-42",
          donor_name: "Amira Hassan",
          section_name: "North Grove",
          plantation_date: "2019-03-12",
          current_age: { years: 7, months: 2 },
          thumbnail_url: null,
        },
      ],
      pagination: {
        page: 1,
        page_size: 24,
        total: 1,
        total_pages: 1,
      },
    }));

    const getPalm = vi.fn(async () => ({
      id: "11111111-1111-4111-8111-111111111111",
      code: "PALM-42",
      plantation_date: "2019-03-12",
      status: "active",
      current_health_status: "healthy",
      description: null,
      current_age: { years: 7, months: 2 },
      donor: { full_name: "Amira Hassan" },
      section: { name: "North Grove", location_name: null, image_url: null },
      images: [],
      harvest_summary: {
        total_amount: "10",
        total_revenue: "100",
        records_count: 1,
      },
      diseases: [],
      children: [],
    }));

    const client = createMockClient({ search, getPalm });
    renderSearchPage(client, "/search?q=Amira");

    expect(await screen.findByRole("heading", { name: /search palms/i })).toBeInTheDocument();
    await waitFor(() => expect(search).toHaveBeenCalled());
    expect(await screen.findByRole("heading", { name: "PALM-42" })).toBeInTheDocument();
    expect(screen.getByText(/Amira Hassan/)).toBeInTheDocument();

    await user.click(
      screen.getByRole("link", { name: /view palm palm-42 sponsored by amira hassan/i }),
    );

    expect(await screen.findByRole("heading", { name: "PALM-42", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /palm details/i })).toBeInTheDocument();
  });

  it("renders an empty state when no palms match", async () => {
    const search = vi.fn(async () => ({
      items: [],
      pagination: {
        page: 1,
        page_size: 24,
        total: 0,
        total_pages: 0,
      },
    }));

    renderSearchPage(createMockClient({ search }), "/search?q=zzz");

    expect(await screen.findByRole("heading", { name: /no palms found/i })).toBeInTheDocument();
  });
});
