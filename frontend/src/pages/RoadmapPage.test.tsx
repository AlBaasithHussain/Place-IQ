import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import RoadmapPage from "./RoadmapPage";
import RoadmapSetupPage from "./RoadmapSetupPage";
import { renderWithRouter } from "../test/test-utils";
import {
  generateRoadmap,
  getRoadmap,
  listAnalyses,
  listRoadmaps,
  updateRoadmapTask,
  type RoadmapDetail,
  type RoadmapTask,
} from "../lib/api";

const { useAuthMock } = vi.hoisted(() => ({ useAuthMock: vi.fn() }));

vi.mock("../context/AuthContext", () => ({ useAuth: useAuthMock }));
vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    generateRoadmap: vi.fn(),
    getRoadmap: vi.fn(),
    listAnalyses: vi.fn(),
    listRoadmaps: vi.fn(),
    updateRoadmapTask: vi.fn(),
  };
});

const task: RoadmapTask = {
  id: 10,
  roadmap_id: 2,
  day: 1,
  title: "Learn FastAPI",
  priority: "high",
  estimated_minutes: 60,
  learning_topics: ["FastAPI"],
  practice_tasks: ["Build an API"],
  mini_project: "Create a small service",
  completed: false,
  completed_at: null,
};

const roadmap: RoadmapDetail = {
  id: 2,
  user_id: 1,
  resume_id: 1,
  job_id: 3,
  analysis_id: 4,
  job_title: "Backend Engineer",
  match_score: 70,
  duration_days: 7,
  hours_per_day: 1,
  generation_engine: "heuristic",
  priority_skills: ["FastAPI"],
  summary: "Focus on backend skills",
  created_at: "2026-01-01T00:00:00Z",
  tasks: [task],
  total_estimated_minutes: 60,
  completed_count: 0,
  progress_percentage: 0,
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
  vi.mocked(listAnalyses).mockResolvedValue([
    { id: 4, resume_id: 1, job_id: 3, score: 70, created_at: "2026-01-01T00:00:00Z" },
  ]);
  vi.mocked(listRoadmaps).mockResolvedValue([]);
  vi.mocked(generateRoadmap).mockResolvedValue(roadmap);
  vi.mocked(getRoadmap).mockResolvedValue(roadmap);
  vi.mocked(updateRoadmapTask).mockResolvedValue({
    ...roadmap,
    tasks: [{ ...task, completed: true, completed_at: "2026-01-01T00:01:00Z" }],
    completed_count: 1,
    progress_percentage: 100,
  });
});

it("generates a 14-day roadmap from the selected match", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/roadmaps/setup" element={<RoadmapSetupPage />} />
      <Route path="/roadmaps/:id" element={<p>Roadmap ready</p>} />
    </Routes>,
    ["/roadmaps/setup"],
  );

  await user.click(await screen.findByRole("button", { name: "14 days" }));
  const hours = screen.getByLabelText("Study time per day (hours)");
  await user.clear(hours);
  await user.type(hours, "2");
  await user.click(screen.getByRole("button", { name: "Generate roadmap" }));

  await waitFor(() =>
    expect(generateRoadmap).toHaveBeenCalledWith({
      analysis_id: 4,
      duration_days: 14,
      hours_per_day: 2,
    }),
  );
  expect(await screen.findByText("Roadmap ready")).toBeInTheDocument();
});

it("toggles a roadmap task checkpoint", async () => {
  const user = userEvent.setup();
  renderWithRouter(
    <Routes>
      <Route path="/roadmaps/:id" element={<RoadmapPage />} />
    </Routes>,
    ["/roadmaps/2"],
  );

  const checkbox = await screen.findByRole("checkbox", { name: "Mark day 1 complete" });
  await user.click(checkbox);

  await waitFor(() => expect(updateRoadmapTask).toHaveBeenCalledWith(2, 10, true));
});
