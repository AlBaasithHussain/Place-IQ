import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import JobsPage from "./JobsPage";
import { renderWithRouter } from "../test/test-utils";
import { analyzeJob, listJobs, type JobDetail } from "../lib/api";

const { useAuthMock } = vi.hoisted(() => ({ useAuthMock: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    analyzeJob: vi.fn(),
    listJobs: vi.fn(),
  };
});

beforeEach(() => {
  useAuthMock.mockReturnValue({
    user: { id: 1, name: "Asha", email: "asha@example.com", created_at: "2026-01-01" },
    token: "token",
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(listJobs).mockResolvedValue([]);
  vi.mocked(analyzeJob).mockResolvedValue({ id: 9 } as JobDetail);
});

it("analyzes a pasted job description", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/jobs" element={<JobsPage />} />
      <Route path="/jobs/:id" element={<p>Job created</p>} />
    </Routes>,
    ["/jobs"],
  );

  await user.click(screen.getByRole("button", { name: "Try a sample" }));
  await user.click(screen.getByRole("button", { name: "Analyze job" }));

  await waitFor(() =>
    expect(analyzeJob).toHaveBeenCalledWith(expect.stringContaining("Senior Python Developer")),
  );
  expect(await screen.findByText("Job created")).toBeInTheDocument();
});

it("disables analysis until the description is long enough", async () => {
  const user = userEvent.setup();
  renderWithRouter(<JobsPage />, ["/jobs"]);

  await user.type(screen.getByPlaceholderText("Paste the full job description here…"), "Too short");
  expect(screen.getByRole("button", { name: "Analyze job" })).toBeDisabled();
  expect(analyzeJob).not.toHaveBeenCalled();
});
