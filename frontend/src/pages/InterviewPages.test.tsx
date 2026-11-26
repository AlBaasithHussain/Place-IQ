import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import InterviewSetupPage from "./InterviewSetupPage";
import InterviewSessionPage from "./InterviewSessionPage";
import { renderWithRouter } from "../test/test-utils";
import {
  answerInterviewQuestion,
  getInterview,
  getInterviewResults,
  listInterviews,
  listJobs,
  listResumes,
  startInterview,
  type InterviewDetail,
} from "../lib/api";

const { useAuthMock } = vi.hoisted(() => ({ useAuthMock: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    answerInterviewQuestion: vi.fn(),
    getInterview: vi.fn(),
    getInterviewResults: vi.fn(),
    listInterviews: vi.fn(),
    listJobs: vi.fn(),
    listResumes: vi.fn(),
    startInterview: vi.fn(),
  };
});

const interview: InterviewDetail = {
  id: 5,
  user_id: 1,
  resume_id: 1,
  job_id: 3,
  job_title: "Backend Engineer",
  question_count: 1,
  generation_engine: "heuristic",
  status: "in_progress",
  created_at: "2026-01-01T00:00:00Z",
  completed_at: null,
  questions: [
    {
      id: 20,
      interview_id: 5,
      position: 1,
      category: "technical",
      question: "Explain REST APIs.",
      focus_skill: "FastAPI",
      answer: null,
      answered_at: null,
    },
  ],
  answered_count: 0,
  progress_percentage: 0,
  current_question_number: 1,
  is_complete: false,
  has_evaluation: false,
};

beforeEach(() => {
  useAuthMock.mockReturnValue({
    user: { id: 1, name: "Asha", email: "asha@example.com", created_at: "2026-01-01" },
    token: "token",
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
  vi.mocked(listResumes).mockResolvedValue([
    {
      id: 1,
      original_filename: "resume.pdf",
      file_size: 100,
      created_at: "2026-01-01T00:00:00Z",
      name: "Asha",
      email: "asha@example.com",
    },
  ]);
  vi.mocked(listJobs).mockResolvedValue([
    {
      id: 3,
      job_title: "Backend Engineer",
      analysis_engine: "heuristic",
      created_at: "2026-01-01T00:00:00Z",
    },
  ]);
  vi.mocked(listInterviews).mockResolvedValue([]);
  vi.mocked(startInterview).mockResolvedValue(interview);
  vi.mocked(getInterview).mockResolvedValue(interview);
  vi.mocked(getInterviewResults).mockResolvedValue(null as never);
  vi.mocked(answerInterviewQuestion).mockResolvedValue({
    ...interview,
    status: "completed",
    is_complete: true,
    current_question_number: null,
    answered_count: 1,
    progress_percentage: 100,
    questions: [
      {
        ...interview.questions[0],
        answer: "REST APIs expose resources over HTTP.",
        answered_at: "2026-01-01T00:01:00Z",
      },
    ],
  });
});

it("starts an interview with the selected resume and job", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/interviews/start" element={<InterviewSetupPage />} />
      <Route path="/interviews/:id" element={<p>Interview ready</p>} />
    </Routes>,
    ["/interviews/start"],
  );

  await user.click(await screen.findByRole("button", { name: "Start interview" }));

  await waitFor(() =>
    expect(startInterview).toHaveBeenCalledWith({
      resume_id: 1,
      job_id: 3,
      question_count: 5,
    }),
  );
  expect(await screen.findByText("Interview ready")).toBeInTheDocument();
});

it("submits an answer from the interview session", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/interviews/:id" element={<InterviewSessionPage />} />
    </Routes>,
    ["/interviews/5"],
  );

  const answer = await screen.findByLabelText("Your answer");
  await user.type(answer, "REST APIs expose resources over HTTP.");
  await user.click(screen.getByRole("button", { name: "Finish interview" }));

  await waitFor(() =>
    expect(answerInterviewQuestion).toHaveBeenCalledWith(
      5,
      20,
      "REST APIs expose resources over HTTP.",
    ),
  );
  expect(answer).toHaveAttribute("maxLength", "10000");
});
