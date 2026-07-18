import { describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { LoginPage } from "@/pages/auth/LoginPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { createMockClient, renderWithProviders } from "@/test/render";

describe("LoginPage", () => {
  it("validates required fields before submit", async () => {
    const user = userEvent.setup();
    const login = vi.fn();

    renderWithProviders(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>,
      {
        route: "/login",
        client: createMockClient({ login }),
      },
    );

    const form = (await screen.findByRole("button", { name: /sign in/i }))
      .closest("form") as HTMLElement;

    await user.click(within(form).getByRole("button", { name: /sign in/i }));

    expect(
      await within(form).findByText("Invalid email address"),
    ).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });
});

describe("ResetPasswordPage", () => {
  it("requires matching passwords before submit", async () => {
    const user = userEvent.setup();
    const client = createMockClient();
    const resetSpy = vi
      .spyOn(client.auth, "resetPassword")
      .mockResolvedValue({ password_reset: true });

    renderWithProviders(
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Routes>,
      {
        route: "/reset-password?token=abcdefghijklmnopqrstuvwxyz012345",
        client,
      },
    );

    const form = (await screen.findByRole("button", { name: /update password/i }))
      .closest("form") as HTMLElement;

    const token = form.querySelector('input[name="token"]') as HTMLInputElement;
    const password = form.querySelector(
      'input[name="password"]',
    ) as HTMLInputElement;
    const confirm = form.querySelector(
      'input[name="confirm_password"]',
    ) as HTMLInputElement;

    await user.clear(token);
    await user.type(token, "abcdefghijklmnopqrstuvwxyz012345");
    await user.type(password, "SuperSecurePass1");
    await user.type(confirm, "DifferentPass123");
    await user.click(within(form).getByRole("button", { name: /update password/i }));

    expect(
      await within(form).findByText("Passwords must match."),
    ).toBeInTheDocument();
    expect(resetSpy).not.toHaveBeenCalled();
  });
});
