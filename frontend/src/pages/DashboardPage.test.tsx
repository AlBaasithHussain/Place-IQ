import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import DashboardPage from "./DashboardPage";
import { renderWithRouter } from "../test/test-utils";
import { getDashboard, type DashboardData } from "../lib/api";

const { useAuthMock } = vi.hoisted(() => ({ useAuthMock: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getDashboard: vi.fn(),
  };
});

const dashboard: DashboardData = {
  has_data: true,
  overview: {
    resume_score: 80,
    resume_file_name: "resume.pdf",
    job_match_score: 70,
    interview_score: 75,
    skills_learned: 4,
    learned_skills: ["Python", "SQL"],
    latest_analysis_id: 3,
    latest_interview_id: 5,
  },
  readiness: {
    score: 72,
    band: "Job-ready with gaps",
    formula: "Placement Readiness = Skill Match 30% + Interview Performance 25%",
    components: [
      {
        key: "skill_match",
        label: "Skill Match",
        weight: 0.3,
        score: 70,
        contribution: 21,
      },
    ],
  },
  skill_analysis: {
    analysis_id: 3,
    job_title: "Backend Engineer",
    strong_skills: [{ skill: "Python", requirement_type: "required" }],
    partial_skills: [],
    missing_skills: [{ skill: "Docker", requirement_type: "preferred" }],
  },
  learning_progress: {
    has_roadmap: true,
    roadmap_id: 2,
    job_title: "Backend Engineer",
    duration_days: 7,
    total_tasks: 10,
    completed_tasks: 4,
    remaining_tasks: 6,
    progress_percentage: 40,
    priority_skills: ["Docker"],
    summary: "Focus on Docker",
  },
  interview: {
    sessions: 2,
    completed_sessions: 1,
    questions_attempted: 5,
    questions_total: 10,
    evaluated_sessions: 1,
    average_score: 75,
    latest_score: 75,
  },
  recent_jobs: [
    {
      id: 3,
      job_title: "Backend Engineer <script>alert(1)</script>",
      analysis_engine: "heuristic",
      created_at: "2026-01-01T00:00:00Z",
      match_score: 70,
    },
  ],
  target_skills: {
    total_jobs: 2,
    skills: [
      {
        skill: "Python",
        job_count: 2,
        total_jobs: 2,
        frequency_percentage: 100,
        requirement_types: ["required"],
        required_count: 2,
        preferred_count: 0,
      },
    ],
  },
  trends: {
    match_scores: [{ label: "Backend Engineer", value: 70 }],
    interview_scores: [{ label: "Interview", value: 75 }],
  },
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
  vi.mocked(getDashboard).mockResolvedValue(dashboard);
});

it("renders readiness and target-skill dashboard data", async () => {
  renderWithRouter(
    <Routes>
      <Route path="/dashboard" element={<DashboardPage />} />
    </Routes>,
    ["/dashboard"],
  );

  expect(await screen.findByText("Job-ready with gaps")).toBeInTheDocument();
  expect(screen.getByText("Top Skills Needed Across My Target Jobs")).toBeInTheDocument();
  expect(screen.getByText("2/2 jobs · 100%")).toBeInTheDocument();
  expect(screen.getByText("Backend Engineer <script>alert(1)</script>")).toBeInTheDocument();
  expect(document.body.innerHTML).not.toContain("<script>alert(1)</script>");
});
