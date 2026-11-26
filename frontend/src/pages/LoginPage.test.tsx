import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import LoginPage from "./LoginPage";
import { renderWithRouter } from "../test/test-utils";

const { loginMock, useAuthMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  useAuthMock: vi.fn(),
}));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));

beforeEach(() => {
  useAuthMock.mockReturnValue({
    user: null,
    token: null,
    loading: false,
    login: loginMock,
    register: vi.fn(),
    logout: vi.fn(),
  });
  loginMock.mockResolvedValue(undefined);
});

it("submits login credentials and navigates to the profile", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/profile" element={<p>Profile ready</p>} />
    </Routes>,
    ["/login"],
  );

  await user.type(screen.getByLabelText("Email"), "asha@example.com");
  await user.type(screen.getByLabelText("Password"), "Passw0rd1");
  await user.click(screen.getByRole("button", { name: "Log in" }));

  expect(loginMock).toHaveBeenCalledWith({
    email: "asha@example.com",
    password: "Passw0rd1",
  });
  expect(await screen.findByText("Profile ready")).toBeInTheDocument();
});
