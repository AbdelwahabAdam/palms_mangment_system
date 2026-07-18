import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";

import { AuthGuard } from "@/auth/AuthGuard";
import { PERMISSIONS } from "@/auth/permissions";
import {
  createMockClient,
  makeUser,
  renderWithProviders,
} from "@/test/render";

describe("AuthGuard", () => {
  it("redirects unauthenticated users to login", async () => {
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<div>Login screen</div>} />
        <Route element={<AuthGuard />}>
          <Route path="/overview" element={<div>Overview secret</div>} />
        </Route>
      </Routes>,
      {
        route: "/overview",
        client: createMockClient(),
      },
    );

    expect(await screen.findByText("Login screen")).toBeInTheDocument();
    expect(screen.queryByText("Overview secret")).not.toBeInTheDocument();
  });

  it("renders protected content for authenticated users", async () => {
    renderWithProviders(
      <Routes>
        <Route element={<AuthGuard />}>
          <Route path="/overview" element={<div>Overview secret</div>} />
        </Route>
      </Routes>,
      {
        route: "/overview",
        client: createMockClient({
          me: async () => makeUser(),
        }),
      },
    );

    expect(await screen.findByText("Overview secret")).toBeInTheDocument();
  });

  it("blocks authenticated users missing the required permission", async () => {
    renderWithProviders(
      <Routes>
        <Route element={<AuthGuard permission={PERMISSIONS.usersRead} />}>
          <Route path="/users" element={<div>Users secret</div>} />
        </Route>
      </Routes>,
      {
        route: "/users",
        client: createMockClient({
          me: async () => makeUser({ permissions: ["palms.read"] }),
        }),
      },
    );

    await waitFor(() => {
      expect(screen.getByText("Access denied")).toBeInTheDocument();
    });
    expect(screen.queryByText("Users secret")).not.toBeInTheDocument();
  });
});
