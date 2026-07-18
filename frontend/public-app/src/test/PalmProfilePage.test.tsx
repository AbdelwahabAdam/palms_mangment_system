import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createMockClient, renderPalmProfile } from "@/test/test-utils";

const palmProfile = {
  id: "22222222-2222-4222-8222-222222222222",
  code: "PALM-42",
  plantation_date: "2019-03-12",
  status: "active",
  current_health_status: "healthy",
  description: "A thriving sponsored palm.",
  current_age: { years: 7, months: 2 },
  donor: { full_name: "Amira Hassan" },
  section: {
    name: "North Grove",
    location_name: "Siwa Oasis",
    image_url: null,
  },
  images: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      thumbnail_url: "https://example.com/thumb.jpg",
      medium_url: "https://example.com/medium.jpg",
      full_url: "https://example.com/full.jpg",
      webp_url: "https://example.com/full.webp",
      uploaded_at: "2024-01-01T00:00:00Z",
    },
  ],
  harvest_summary: {
    total_amount: "120.5",
    total_revenue: "4500",
    records_count: 4,
  },
  diseases: [
    {
      disease_name: "Bayoud",
      detected_at: "2022-06-01",
      status: "resolved",
      notes: "Treated early.",
      treatments: [
        {
          treatment_name: "Soil treatment",
          treatment_date: "2022-06-15",
          notes: null,
        },
      ],
    },
  ],
  children: [
    {
      id: "44444444-4444-4444-8444-444444444444",
      code: "PALM-43",
      relationship_type: "offshoot",
    },
  ],
};

describe("PalmProfilePage", () => {
  it("renders profile sections and related palm navigation", async () => {
    const user = userEvent.setup();
    const getPalm = vi.fn(async () => palmProfile);
    const client = createMockClient({ getPalm });

    renderPalmProfile(client, "PALM-42");

    await waitFor(() => expect(getPalm).toHaveBeenCalled());
    expect(await screen.findByRole("heading", { name: "PALM-42", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /palm details/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /harvest & revenue/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /disease timeline/i })).toBeInTheDocument();
    expect(screen.getByText("Bayoud")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Amira Hassan" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "North Grove" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open photo 1 of 1/i })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "PALM-43" }));
    await waitFor(() =>
      expect(getPalm).toHaveBeenCalledWith("PALM-43", expect.anything()),
    );
  });

  it("shows a not-found empty state when the palm is missing", async () => {
    const { ApiError } = await import("@palms/shared");
    const getPalm = vi.fn(async () => {
      throw new ApiError({
        status: 404,
        code: "not_found",
        message: "Palm not found",
      });
    });

    renderPalmProfile(createMockClient({ getPalm }), "MISSING");

    expect(await screen.findByRole("heading", { name: /palm not found/i })).toBeInTheDocument();
  });
});
