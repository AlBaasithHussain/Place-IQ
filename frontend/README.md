# Frontend — PrepPilot (React + TypeScript + Tailwind)

## Setup

```powershell
# from placement-prep\frontend
copy .env.example .env
npm install
```

## Run

```powershell
npm run dev
```

App: http://localhost:5173

## Routes

| Path        | Page         | Access    |
| ----------- | ------------ | --------- |
| `/`         | LandingPage  | public    |
| `/login`    | LoginPage    | public    |
| `/register` | RegisterPage | public    |
| `/dashboard` | DashboardPage | protected |
| `/profile`  | ProfilePage  | protected |
| `/resumes`  | ResumesPage  | protected |
| `/resumes/:id` | ResumeDetailPage | protected |
| `/jobs`     | JobsPage     | protected |
| `/jobs/:id` | JobDetailPage | protected |
| `/analysis/new` | MatchSetupPage | protected |
| `/analysis/:id` | MatchResultPage | protected |
| `/roadmaps/new` | RoadmapSetupPage | protected |
| `/roadmaps/:id` | RoadmapPage | protected |
| `/interviews/start` | InterviewSetupPage | protected |
| `/interviews/:id` | InterviewSessionPage | protected |
| `/interviews/:id/results` | InterviewResultsPage | protected |
| `*`         | NotFoundPage | public    |

`ProtectedRoute` redirects unauthenticated users to `/login`.

## Dashboard

- `/dashboard` calls `GET /api/v1/dashboard` and is linked from the navbar.
- Overview cards show resume score, latest job match score, latest interview
  score and skills learned, each with progress bars and deep links where data exists.
- Score trends and learning progress use dependency-free SVG donut/line charts;
  no chart library was added.
- Skill analysis shows strong/partial/missing bars plus a responsive table with
  requirement types from the latest match.
- Learning progress shows the latest 7-day roadmap with completed/remaining task
  counts, a progress ring and priority skills.
- Interview stats show questions attempted, average score, latest score and a
  score trend chart.
- Job analysis shows the five newest analyzed jobs in a responsive table with
  match scores.
- Placement Readiness shows a donut score, band, formula and weighted component
  bars from the dashboard API.
- Top Skills Needed Across My Target Jobs shows horizontal frequency bars with
  job counts, percentages and required/preferred breakdowns.
- Loading skeletons, section-level empty states, a global empty state and a
  retryable error banner are implemented.

## Resumes

- `/resumes` lets the user pick a PDF (client-side `.pdf` + 5 MB check) and
  uploads it via `FormData` (`POST /api/v1/resumes/upload`), then redirects to
  the detail page. The list shows name/email/size/date.
- `/resumes/:id` shows parsed skills/categories and education, projects,
  certifications and experience, plus the extracted raw text.
- The shared Axios instance no longer sets a default `Content-Type`, so the
  browser adds the multipart boundary automatically for uploads.

## Job descriptions

- `/jobs` has a large textarea (30–20,000 chars, character counter, "Try a
  sample") and calls `POST /api/v1/jobs/analyze`, then opens the saved result.
- Saved analyses are listed with their engine badge ("AI analysis" or
  "Heuristic preview").
- `/jobs/:id` renders required/preferred skills, technology categories, soft
  skills, experience/education requirements, and the original JD text.
- When AI is not configured the detail page explains that the rule-based
  fallback was used.
- The job detail page has a **Match resume →** button that preselects that JD.

## Matching

- `/analysis/new` lists saved resumes and analyzed jobs, lets the user choose
  both, and calls `POST /api/v1/analysis/match`. It also accepts `?jobId=` to
  preselect a job from the job detail page.
- `/analysis/:id` fetches the saved result via `GET /api/v1/analysis/{id}`.
- The result page shows the 0–100 score card, per-category progress bars with
  weights and points, a skill comparison table, separate matching / partial /
  missing / bonus skill lists, and the written score explanation.
- It also has a **Start mock interview →** button that preselects the same resume
  and job.
- The score is calculated by backend rules; the AI is never asked to generate it.

## Learning roadmaps

- The match result page has a **Generate roadmap →** button that preselects the
  saved match. `/roadmaps/new` also lists matches and saved plans.
- The setup form chooses 7 or 14 days and `0.25`–`8` study hours per day, then
  calls `POST /api/v1/roadmaps/generate`.
- `/roadmaps/:id` shows progress percentage, priority skills, the AI/local
  engine badge, and one card per day with learning topics, practice tasks, a
  mini project, estimated time, priority level and a completion checkbox.
- Checking a day calls `PATCH /api/v1/roadmaps/{id}/tasks/{task_id}` so progress
  persists across reloads.

## Mock interviews

- `/interviews/start` lists saved resumes, jobs and past sessions, accepts
  `?resumeId=` and `?jobId=`, and chooses `5`–`10` questions before calling
  `POST /api/v1/interviews/start`.
- `/interviews/:id` fetches the saved session, highlights the first unanswered
  question, and submits text answers with `POST /api/v1/interviews/{id}/answer`.
- The session page shows category/focus badges, answer progress, an answer text
  area, automatic next-question flow, a completion summary, and all saved
  answers for review.
- Completed sessions can call `POST /api/v1/interviews/{id}/evaluate` from the
  **Evaluate answers** button and then open `/interviews/:id/results`.
- The setup page links past sessions to their saved results when
  `has_evaluation` is true.
- `/interviews/:id/results` loads `GET /api/v1/interviews/{id}/results` and shows
  the overall score, strengths, weaknesses, suggested improvements, AI/local
  engine badge, model answers, original answers and four criterion bars per
  question (`technical_accuracy`, `relevance`, `completeness`, `clarity`).
- The UI explicitly states that evaluation covers answer content only, not
  emotions or personality. The navbar has an **Interview** link. Voice answers
  are not implemented.

## Auth

- `AuthContext` stores the JWT in `localStorage` and hydrates the user via
  `GET /auth/me` on load.
- An Axios request interceptor attaches `Authorization: Bearer <token>`.
- Register/login auto-login; logout clears the token and calls the API.
- Tokens are sent only on protected API paths and cleared after a `401`.
- Forms disable duplicate submissions, resume uploads are checked before API
  calls, interview answers are capped at 10,000 characters, and the document
  declares a content security policy.

## Testing

```powershell
npm test
```

- Vitest + React Testing Library cover 12 tests across login, registration,
  resume upload, job analysis, dashboard, roadmap and interview flows.

## Build / typecheck

```powershell
npm run typecheck
npm run build
npm run preview
```

## Env

- `VITE_API_BASE_URL` (in `.env`) points to the FastAPI backend.
