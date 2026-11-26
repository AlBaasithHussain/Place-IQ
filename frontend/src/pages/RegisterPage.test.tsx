import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import RegisterPage from "./RegisterPage";
import { renderWithRouter } from "../test/test-utils";

const { registerMock, useAuthMock } = vi.hoisted(() => ({
  registerMock: vi.fn(),
  useAuthMock: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));

beforeEach(() => {
  useAuthMock.mockReturnValue({
    user: null,
    token: null,
    loading: false,
    login: vi.fn(),
    register: registerMock,
    logout: vi.fn(),
  });
  registerMock.mockResolvedValue(undefined);
});

it("registers a user and navigates to the profile", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/profile" element={<p>Profile ready</p>} />
    </Routes>,
    ["/register"],
  );

  await user.type(screen.getByLabelText("Full name"), "Asha Verma");
  await user.type(screen.getByLabelText("Email"), "asha@example.com");
  await user.type(screen.getByLabelText("Password"), "Passw0rd1");
  await user.type(screen.getByLabelText("Confirm password"), "Passw0rd1");
  await user.click(screen.getByRole("button", { name: "Create account" }));

  expect(registerMock).toHaveBeenCalledWith({
    name: "Asha Verma",
    email: "asha@example.com",
    password: "Passw0rd1",
  });
  expect(await screen.findByText("Profile ready")).toBeInTheDocument();
});

it("blocks mismatched passwords before calling the API", async () => {
  const user = userEvent.setup();
  renderWithRouter(<RegisterPage />, ["/register"]);

  await user.type(screen.getByLabelText("Full name"), "Asha Verma");
  await user.type(screen.getByLabelText("Email"), "asha@example.com");
  await user.type(screen.getByLabelText("Password"), "Passw0rd1");
  await user.type(screen.getByLabelText("Confirm password"), "Passw0rd2");
  await user.click(screen.getByRole("button", { name: "Create account" }));

  expect(registerMock).not.toHaveBeenCalled();
  expect(screen.getByText("Passwords do not match.")).toBeInTheDocument();
});
