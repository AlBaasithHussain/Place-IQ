import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import ResumesPage from "./ResumesPage";
import { renderWithRouter } from "../test/test-utils";
import { listResumes, uploadResume, type ResumeDetail } from "../lib/api";

const { useAuthMock } = vi.hoisted(() => ({ useAuthMock: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    listResumes: vi.fn(),
    uploadResume: vi.fn(),
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
  vi.mocked(listResumes).mockResolvedValue([]);
  vi.mocked(uploadResume).mockResolvedValue({ id: 7 } as ResumeDetail);
});

it("uploads a selected PDF resume", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/resumes" element={<ResumesPage />} />
      <Route path="/resumes/:id" element={<p>Resume loaded</p>} />
    </Routes>,
    ["/resumes"],
  );

  const file = new File([new Uint8Array([37, 80, 68, 70, 45])], "resume.pdf", {
    type: "application/pdf",
  });
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  await user.upload(input, file);
  await user.click(screen.getByRole("button", { name: "Upload & analyze" }));

  await waitFor(() => expect(uploadResume).toHaveBeenCalledWith(file));
  expect(await screen.findByText("Resume loaded")).toBeInTheDocument();
});

it("rejects a non-PDF file before calling the API", async () => {
  renderWithRouter(<ResumesPage />, ["/resumes"]);

  const file = new File(["not a resume"], "resume.txt", { type: "text/plain" });
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });

  expect(await screen.findByText("Please choose a PDF file.")).toBeInTheDocument();
  expect(uploadResume).not.toHaveBeenCalled();
});
