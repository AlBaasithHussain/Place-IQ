# Backend — Placement Prep API (FastAPI)

## Setup (Windows PowerShell)

```powershell
# from placement-prep\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt      # add requirements-dev.txt for tests
copy .env.example .env               # then edit DATABASE_URL / SECRET_KEY
```

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on startup. You can also run them manually:

```powershell
python -m app.db.init_db
```

## Endpoints

| Method | Path                     | Auth | Notes                          |
| ------ | ------------------------ | ---- | ------------------------------ |
| POST   | `/api/v1/auth/register`  | —    | 201 + JWT                      |
| POST   | `/api/v1/auth/login`     | —    | 200 + JWT                      |
| GET    | `/api/v1/auth/me`        | ✅   | Current user                   |
| POST   | `/api/v1/auth/logout`    | ✅   | Stateless ack                  |
| GET    | `/api/v1/profile/me`     | ✅   | Student profile                |
| PUT    | `/api/v1/profile/me`     | ✅   | Partial update                 |
| POST   | `/api/v1/resumes/upload` | ✅   | Multipart PDF → parsed & stored |
| GET    | `/api/v1/resumes`        | ✅   | List my resumes (newest first) |
| GET    | `/api/v1/resumes/{id}`   | ✅   | Resume detail (404 if not mine) |
| POST   | `/api/v1/jobs/analyze`   | ✅   | Paste JD text → AI JSON → validated & stored |
| GET    | `/api/v1/jobs`           | ✅   | List my job analyses (newest first) |
| GET    | `/api/v1/jobs/{id}`      | ✅   | Job detail (404 if not mine)   |
| POST   | `/api/v1/analysis/match` | ✅   | Match my resume + job → stored score |
| GET    | `/api/v1/analysis`       | ✅   | List my saved matches (newest first) |
| GET    | `/api/v1/analysis/{id}`  | ✅   | Saved match result (404 if not mine) |
| POST   | `/api/v1/roadmaps/generate` | ✅ | AI roadmap → validated & stored   |
| GET    | `/api/v1/roadmaps`       | ✅   | List my roadmaps with progress    |
| GET    | `/api/v1/roadmaps/{id}`  | ✅   | Roadmap detail + daily tasks      |
| PATCH  | `/api/v1/roadmaps/{id}/tasks/{task_id}` | ✅ | Toggle completion      |
| POST   | `/api/v1/interviews/start` | ✅ | AI questions → validated & stored |
| GET    | `/api/v1/interviews`     | ✅   | List my interviews with progress |
| GET    | `/api/v1/interviews/{id}` | ✅  | Interview detail + answers       |
| POST   | `/api/v1/interviews/{id}/answer` | ✅ | Store one text answer    |
| POST   | `/api/v1/interviews/{id}/evaluate` | ✅ | Evaluate answers → validated & stored |
| GET    | `/api/v1/interviews/{id}/results` | ✅ | Saved evaluation detail    |
| GET    | `/api/v1/dashboard`      | ✅   | Dashboard, readiness and target skills |
| GET    | `/api/v1/health`         | —    | Liveness                       |
| GET    | `/api/v1/health/db`      | —    | DB readiness                   |

Interactive docs: http://localhost:8000/docs

## Test

```powershell
pip install -r requirements-dev.txt
pytest -v
```

- Default: in-memory SQLite (no external services).
- 163 tests total: health/auth/profile, resume parsing/upload, job analysis,
  deterministic matching, roadmap generation (AI validation/repair, local
  curricula, day counts, time budgets, task completion, progress, ownership),
  interviews (AI validation/repair, category coverage, local fallback,
  answer flow, completion, progress, ownership), evaluations (AI/local
  feedback validation, score ranges, repair failure, idempotency, completion
  checks, ownership, results API), dashboard aggregation (auth, empty state,
  scores, skills, tasks, interviews, jobs, trends, ownership isolation), and
   readiness (weights, clamping, bands, technical-preparation blend, target-skill
   frequency and ordering), and security (bcrypt, JWT claims/tampering/audience/
   issuer, SQL-injection payloads, CORS, production config validation, sanitized
   uploads, 5 MB boundary, PDF page/text caps, generic AI/health errors).
- Against PostgreSQL:
  ```powershell
  $env:TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/placement_prep_test"
  pytest
  ```

## Resume pipeline

`app/services/resume/`:

- `pdf.py` — extracts text with **pypdf**; raises `PdfExtractionError`.
- `cleaner.py` — normalises whitespace/line endings.
- `extractor.py` — heuristic parsing into name, email, `programming_languages`,
  `frameworks`, `databases`, `tools`, `skills` (union) and education/projects/
  certifications/experience sections.

`POST /resumes/upload` enforces `.pdf`, non-empty, ≤ 5 MB, `%PDF-` magic bytes,
then stores cleaned text + parsed JSON in the `resumes` table.

## Job description analysis

`app/services/jobs/`:

- `llm.py` — tiny `httpx` client for any OpenAI-compatible
  `POST {LLM_BASE_URL}/chat/completions` endpoint (JSON mode, temperature 0).
- `keywords.py` — shared technology catalogues + cloud/soft-skill catalogues.
- `analyzer.py` — **primary path** asks the LLM for strict JSON, validates it
  against `JobAnalysisResult` (Pydantic), retries once with a repair prompt,
  and raises `JobAnalysisError` on a second failure. **Fallback path** is a
  rule-based extractor used when `LLM_API_KEY` is blank. Results carry
  `analysis_engine` (`llm` / `heuristic`).

`POST /jobs/analyze` stores the original text and validated analysis in the
`jobs` table. Invalid AI output or an unreachable AI service → **502** and
nothing is persisted. Text is limited to 30–20,000 characters.

To enable real AI in `.env`:

```
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

Other compatible providers work too (Groq, OpenRouter, Ollama, etc.).

## Resume ↔ job matching

`app/services/analysis/`:

- `relations.py` — canonicalises skill names and holds the static, curated
  partial-credit map (e.g. `PostgreSQL` ↔ `SQL`, `React` ↔ `Next.js`).
- `scorer.py` — deterministic, LLM-free scoring. Statuses: `match` = 1.0,
  `partial` = 0.5, `missing` = 0.0, averaged per group; empty groups = 1.0.

`POST /analysis/match` accepts `{resume_id, job_id}`, verifies both belong to
the current user, computes the result and stores it in `match_analyses`:

```
score = 70% required skills + 15% preferred skills
      + 10% projects/experience + 5% soft skills   (rounded half-up, 0–100)
```

Projects/experience = 70% years ratio (resume years ÷ required years, capped at
1.0) + 30% keyword overlap with the JD's experience lines. `GET /analysis/{id}`
returns the saved result. Every response includes the full breakdown and a
human-readable explanation. No AI call is made in this flow.

## Roadmap generation

`app/services/roadmaps/`:

- `generator.py` — asks the configured LLM for strict JSON containing priority
  skills and exactly 7 or 14 day objects. `RoadmapPlan` validates the shape,
  day sequence and text limits; invalid output gets one repair retry, then a
  `502` with nothing stored.
- `curriculum.py` — rule-based fallback used when `LLM_API_KEY` is blank. It
  maps missing skills to curated topic sequences and builds the same validated
  shape, tagged `generation_engine: "heuristic"`.

`POST /roadmaps/generate` accepts `{analysis_id, duration_days, hours_per_day}`.
The backend loads the owned match, resume and job, sends the target role,
resume skills, missing/partial skills, match score and study budget to the AI,
then stores the validated plan in `roadmaps` + `roadmap_tasks`.

`GET /roadmaps` lists saved plans with progress; `GET /roadmaps/{id}` returns
daily tasks; `PATCH /roadmaps/{id}/tasks/{task_id}` persists completion and
recomputes the progress percentage. Rows are always filtered by `user_id`.

## Mock interviews

`app/services/interviews/`:

- `generator.py` — asks the configured LLM for strict JSON containing exactly
  `5`–`10` questions. `InterviewPlan` validates count, category values, unique
  question text and cleaned focus skills; invalid output gets one repair retry,
  then a `502` with nothing stored. Every category (`technical`, `hr`,
  `behavioral`, `project_based`, `problem_solving`) must appear at least once.
- The local fallback uses role, resume skills, projects and missing skills to
  build the same validated structure, tagged `generation_engine: "heuristic"`.
- `evaluator.py` — asks the configured LLM for strict JSON evaluating every
  answer on `technical_accuracy`, `relevance`, `completeness` and `clarity`, plus
  overall feedback, strengths, weaknesses, suggested improvements and model
  answers. `InterviewEvaluationDraft` validates one result per question position
  and `0`–`100` scores; invalid output gets one repair retry, then `502`.
- The evaluation fallback uses deterministic answer-length, skill-overlap and
  coverage rules, tagged `generation_engine: "heuristic"`. It never claims to
  assess emotions, personality or other scientific traits.

`POST /interviews/start` accepts `{resume_id, job_id, question_count}`. The
backend verifies ownership, recomputes deterministic gaps with the existing
scorer, generates the questions and stores them in `interviews` +
`interview_questions`. `GET /interviews` lists sessions; `GET /interviews/{id}`
returns questions, stored text answers, progress percentage and the first
unanswered question number. `POST /interviews/{id}/answer` stores one answer and
marks the session `completed` when all questions are answered. Sessions and
questions are always filtered by `user_id`.

`POST /interviews/{id}/evaluate` only works on completed sessions and is
idempotent: repeat calls return the stored result. It writes
`interview_evaluations` + `answer_evaluations` with one row per answer.
`GET /interviews/{id}/results` returns the overall score/summary, strengths,
weaknesses, improvements, model answers, generation engine and all four criterion
scores per question. `GET /interviews` and `GET /interviews/{id}` also expose
`has_evaluation`. Voice answers are not implemented.

## Student dashboard

`GET /dashboard` builds a response from the current user's existing rows; it
makes no AI call and creates no new tables. `app/services/dashboard.py` derives:

- **Overview:** latest resume completeness score, latest job match score, latest
  interview evaluation score, and distinct skills learned from completed roadmap
  learning topics.
- **Skill analysis:** strong/partial/missing skills and requirement types from
  the latest saved match.
- **Learning progress:** completed/remaining tasks, percentage, priority skills
  and summary from the latest 7-day roadmap.
- **Interview:** sessions, answered/total questions, evaluated sessions, average
  score and latest score.
- **Job analysis:** five newest analyzed jobs with their latest saved match score.
- **Trends:** the last six match and interview evaluation scores.
- **Placement Readiness:** score, band, formula and five components from
  `app/services/readiness.py`.
- **Target skills:** top required/preferred skills across all analyzed jobs.

The readiness formula is deterministic:

```
Placement Readiness =
  0.30 × latest job match score +
  0.25 × average interview evaluation overall score +
  0.20 × technical preparation +
  0.15 × latest resume completeness score +
  0.10 × latest 7-day roadmap progress percentage
```

Technical preparation is `0.70 × average answer technical_accuracy` plus
`0.30 × average answer score for problem_solving questions` when such answers
exist; otherwise it is the technical accuracy average. Components and the final
score are clamped to `0`–`100`; the total is rounded. Bands are `80+ Strong`,
`60–79 Job-ready with gaps`, `40–59 Building readiness`, and `0–39 Needs
foundation`.

Target-skill analysis combines `required_skills` and `preferred_skills` from all
the user's jobs, deduplicates each skill per job, computes
`round(job_count × 100 / total_jobs)`, sorts by count then name, and returns the
top 10 with required/preferred counts and requirement types.

Empty accounts return `200` with zeroes and empty lists. Every query is filtered
by `user_id`.

## Quick demo without PostgreSQL

Set in `.env`:
```
DATABASE_URL=sqlite:///./dev.db
```
(app.db is git-ignored). Use PostgreSQL for the real project.

## Notes

- **PostgreSQL** is the target DB; **SQLAlchemy 1.4.54** is pinned because
  SQLAlchemy 2.x's compiled extensions are blocked by Windows Application
  Control on this machine. 1.4 has a pure-Python fallback.
- **PyMuPDF is blocked** here too, so PDF text extraction uses **pypdf** (pure
  Python). Scanned/image-only PDFs yield no text → HTTP 422 (OCR is future work).
- Passwords are hashed with **bcrypt** (cost 12); plaintext is never stored.
- JWTs use **HS256** and `SECRET_KEY`; tokens expire after
  `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60) and require `sub`, `iat`, `exp`,
  `aud`, and `iss` claims.
- CORS uses explicit origins/methods/headers without credentials; API docs are
  disabled in production/staging and production settings are validated at startup.
- Upload filenames are sanitized, MIME is forced server-side, and PDF parsing is
  capped at 50 pages and 2,000,000 characters.
- AI/health failures return generic error details; upstream specifics stay in logs.
- Logout is client-side/stateless in this phase.
- LLM keys are read server-side from `.env` and never returned by the API.
- When no LLM key is set, JD analysis, roadmap recommendations, interview
  questions and answer evaluations use explicit local fallbacks; match scores,
  dashboard metrics, readiness scores and target-skill counts are deterministic
  in every configuration.
