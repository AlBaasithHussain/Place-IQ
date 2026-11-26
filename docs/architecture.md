# Architecture Notes

## Request flow

```
React (Vite :5173) --axios + JWT--> FastAPI (:8000) --SQLAlchemy--> PostgreSQL
   /analysis/*    /roadmaps/*    /interviews/*    /dashboard/*   |
                                               +-- (Phase 4) LLM API, server-side only
                                               +-- (Phase 5) deterministic scorer, no AI
                                               +-- (Phase 6) LLM roadmap + local fallback
                                                +-- (Phase 7) LLM questions + local fallback
                                                  +-- (Phase 8) LLM answer evaluation + local fallback
                                                  +-- (Phase 9) read-only dashboard aggregation, no AI
                                                  +-- (Phase 10) weighted readiness + target skills, no AI
```

- Analyzed data is stored as plain JSON columns so the same code runs on
  PostgreSQL and SQLite (tests use SQLite).

- Public entry point: `GET /api/v1/health`.
- Auth: client sends `Authorization: Bearer <JWT>`; `get_current_user`
  decodes the token, loads the user, and 401s on any failure.

## Layering

| Layer        | Location               | Responsibility                                  |
| ------------ | ---------------------- | ----------------------------------------------- |
| Routes       | `app/api/routes/*`     | HTTP input/output only                          |
| Dependency   | `app/api/deps.py`      | Resolve current user from JWT                   |
| Security     | `app/core/security.py` | bcrypt hashing + JWT encode/decode              |
| Config       | `app/core/config.py`   | Typed settings from `.env`                      |
| Schemas      | `app/schemas/*`        | Pydantic request/response validation            |
| Models       | `app/models/*`         | SQLAlchemy ORM tables                           |
| Services     | `app/services/*`       | Domain logic (PDF → text, JD → JSON, deterministic matching, roadmap generation, interview questions) |
| Persistence  | `app/db/*`             | Engine, session factory, table creation         |

## Data model

**users**: `id` PK, `name`, `email` (unique, lowercased), `password_hash`,
`created_at`, `updated_at`.

**student_profiles**: `user_id` PK + FK → `users.id` (cascade delete),
`college`, `degree`, `branch`, `graduation_year`, `target_role`,
`created_at`, `updated_at`. One-to-one with a user.

**resumes**: `id` PK, `user_id` FK → `users.id` (cascade delete),
`original_filename`, `file_size`, `mime_type`, `raw_text` (cleaned),
`parsed_data` (JSON), `created_at`, `updated_at`. Many per user. The parsed
JSON is plain (no DB-specific type) so it works on both PostgreSQL and SQLite.

**jobs**: `id` PK, `user_id` FK → `users.id` (cascade delete), `job_title`,
`original_text`, ten JSON list columns (required/preferred skills, languages,
frameworks, databases, cloud, tools, soft skills, experience, education),
`analysis_engine` (`llm` / `heuristic`), `created_at`, `updated_at`.

**match_analyses**: `id` PK, `user_id` FK → `users.id` (cascade delete),
`resume_id` FK → `resumes.id` (cascade delete), `job_id` FK → `jobs.id`
(cascade delete), `score` (integer 0–100), `result` (JSON with comparisons,
gap lists, breakdown and explanation), `created_at`. Many per user; reads are
filtered by `user_id`.

**roadmaps**: `id` PK, `user_id` FK → `users.id`, `resume_id` FK → `resumes.id`,
`job_id` FK → `jobs.id`, `analysis_id` FK → `match_analyses.id` (all cascade
delete), `job_title`, `match_score`, `duration_days` (7/14), `hours_per_day`,
`generation_engine` (`llm` / `heuristic`), `priority_skills` (JSON), `summary`,
`created_at`.

**roadmap_tasks**: `id` PK, `roadmap_id` FK → `roadmaps.id` (cascade delete),
`day`, `title`, `priority` (`high`/`medium`/`low`), `estimated_minutes`,
`learning_topics` (JSON), `practice_tasks` (JSON), `mini_project`, `completed`,
`completed_at`. Many per roadmap; ordered by `day`.

**interviews**: `id` PK, `user_id` FK → `users.id`, `resume_id` FK →
`resumes.id`, `job_id` FK → `jobs.id` (all cascade delete), `job_title`,
`question_count` (5–10), `generation_engine` (`llm` / `heuristic`), `status`
(`in_progress` / `completed`), `completed_at`, `created_at`. Many per user.

**interview_questions**: `id` PK, `interview_id` FK → `interviews.id` (cascade
delete), `position`, `category` (one of five values), `question`, `focus_skill`,
`answer` (nullable text), `answered_at`. Many per interview; ordered by
`position`.

**interview_evaluations**: `id` PK, `interview_id` FK → `interviews.id`
(cascade delete, unique), `generation_engine` (`llm` / `heuristic`),
`overall_score` (0–100), `overall_summary`, `overall_strengths` (JSON),
`overall_weaknesses` (JSON), `suggested_improvements` (JSON), `created_at`,
`updated_at`. One per interview.

**answer_evaluations**: `id` PK, `evaluation_id` FK →
`interview_evaluations.id` (cascade delete), `question_id` FK →
`interview_questions.id` (cascade delete), unique `(evaluation_id, position)`,
`position`, `technical_accuracy`, `relevance`, `completeness`, `clarity`
(0–100 each), `score` (0–100), `strengths` (JSON), `weaknesses` (JSON),
`suggested_improvement`, `model_answer`, `created_at`. One per evaluated answer.

## Resume parsing pipeline

```
UploadFile ──► validate (.pdf, size ≤ 5 MB, %PDF- magic)
           ──► pypdf text extraction        (services/resume/pdf.py)
           ──► clean_text (whitespace)      (services/resume/cleaner.py)
           ──► extract_resume_data (heuristics) (services/resume/extractor.py)
           ──► ParsedResume validation ──► resumes.raw_text + resumes.parsed_data
```

The extractor uses a curated technology catalogue (canonical name → aliases)
with word-boundary matching (single letters `C`, `R`, `Go` are case-sensitive)
and section headings to pull education, projects, certifications and
experience. Deliberately rule-based: fast, dependency-free and explainable;
LLM-assisted extraction can augment it later.

## Job analysis pipeline

```
Pasted text ──► Pydantic input validation (30–20,000 chars)
            ──► LLM client (httpx, OpenAI-compatible /chat/completions, JSON mode)
            ──► strict JSON contract (JobAnalysisResult) ──► retry once on failure
            ──► jobs table (original text + validated JSON + engine tag)
```

`JobAnalysisResult` is the single contract shared by the AI prompt, the
validator and the API response: exact keys, string lists only, deduplicated and
trimmed. If the model returns prose, code fences or the wrong schema, the
service retries with a repair instruction; a second failure produces **502**
and no row is written. When `LLM_API_KEY` is blank, `analyze_heuristic` uses the
same technology catalogues as resume parsing plus cloud/soft-skill catalogues,
and section headings to split required vs preferred skills. The rule-based
result is tagged `analysis_engine: "heuristic"` so it is never confused with AI.

## Matching pipeline

```
{resume_id, job_id} ──► ownership checks (404 on not-owned rows)
                    ──► canonicalise resume + job skills (services/analysis/relations.py)
                    ──► classify match / partial / missing
                    ──► years credit + keyword overlap (services/analysis/scorer.py)
                    ──► weighted score, breakdown, gap lists, explanation
                    ──► match_analyses table ──► GET /analysis/{id}
```

The partial map is static data, not AI output. Weights are 70% required, 15%
preferred, 10% projects/experience, 5% soft skills; each group's credit is the
mean of its statuses (1.0 / 0.5 / 0.0), with empty groups scoring 1.0. The
weighted sum is multiplied by 100 and rounded half-up. This makes results
reproducible and explainable, and guarantees the LLM never generates the score.

## Roadmap generation pipeline

```
{analysis_id, duration_days, hours_per_day} ──► ownership checks (404)
   ──► load match score + gap lists + target job + resume skills
   ──► model prompt (role, gaps, score, study budget)
   ──► LLM JSON ──► RoadmapPlan validation + one repair retry
   ──► normalise day count/sequence and cap minutes to budget
   ──► roadmaps + roadmap_tasks rows
   ──► PATCH task completion ──► server-derived progress percentage
```

When `LLM_API_KEY` is blank, `generate_heuristic` uses the static curricula in
`curriculum.py` to produce the same validated structure. AI output is never
trusted: it must satisfy `RoadmapPlan` before any row is written, and a second
validation failure returns **502** with no partial persistence.

## Mock interview pipeline

```
{resume_id, job_id, question_count} ──► ownership checks (404)
   ──► deterministic scorer recomputes missing skills
   ──► model prompt (role, JD, resume skills, projects, gaps, score)
   ──► LLM JSON ──► InterviewPlan validation + one repair retry
   ──► interviews + interview_questions rows
   ──► POST answer ──► stored text + server-derived progress/completion
```

`InterviewPlan` requires the exact requested count, unique question text and at
least one of `technical`, `hr`, `behavioral`, `project_based` and
`problem_solving`. Empty `focus_skill` values are filled from missing/required
resume skills before storage. When `LLM_API_KEY` is blank, `generate_heuristic`
uses role, skills, projects and gaps to build the same validated structure.
Answers are plain text only; voice is future work.

## Answer evaluation pipeline

```
POST /interviews/{id}/evaluate ──► completed + ownership checks (400/404)
   ──► stored evaluation exists? ──► return it unchanged (idempotent)
   ──► model prompt (role, JD, required skills + every answer)
   ──► LLM JSON ──► InterviewEvaluationDraft validation + one repair retry
   ──► interview_evaluations + answer_evaluations rows
   ──► GET /interviews/{id}/results ──► overall feedback + criteria per answer
```

`InterviewEvaluationDraft` requires one item per answered position, unique
positions, four `0`–`100` criteria, an `0`–`100` overall score, non-empty
feedback lists, a suggested improvement and a model answer. Invalid AI output
gets one repair retry, then **502** with no stored rows. When `LLM_API_KEY` is
blank, `generate_heuristic` applies transparent length, skill-overlap and
coverage rules and tags the result `generation_engine: "heuristic"`. The prompt
and UI forbid emotion/personality/scientific-trait claims; evaluation covers
answer content only.

## Dashboard aggregation pipeline

```
GET /dashboard ──► JWT user id ──► ownership-filtered reads across six tables
   ──► deterministic resume completeness score
   ──► latest match score + strong/partial/missing skills
   ──► latest 7-day roadmap + completed/remaining tasks
   ──► interview attempt/score stats + answer technical accuracy
   ──► five newest jobs + latest match scores
   ──► weighted readiness components + band
   ──► target-skill frequency across all jobs
   ──► DashboardData → React cards, SVG charts, progress bars and tables
```

The dashboard endpoint is read-only: it creates no rows, makes no LLM call and
returns zeroes/empty lists for new users. `Skills Learned` is the count of
distinct learning topics from completed roadmap tasks. Score trends are the last
six match and evaluation scores in chronological order.

### Placement readiness formula

```
Placement Readiness =
  0.30 × latest job match score +
  0.25 × average interview evaluation overall score +
  0.20 × technical preparation +
  0.15 × latest resume completeness score +
  0.10 × latest 7-day roadmap progress percentage
```

`technical preparation = 0.70 × average answer technical_accuracy` plus
`0.30 × average answer score for problem_solving questions` when such answers
exist; otherwise it is the technical accuracy average. Every component and the
final score are clamped to `0`–`100`, and the final score is rounded. Bands are
`80+ Strong`, `60–79 Job-ready with gaps`, `40–59 Building readiness`, and
`0–39 Needs foundation`.

Target skills combine required and preferred skills from all analyzed jobs,
deduplicate per job, calculate `round(job_count × 100 / total_jobs)`, sort by
count then case-insensitive name, and keep the top 10.

## Security decisions

- **bcrypt** (cost 12) for password hashing; plaintext is never logged or stored.
- **PyJWT / HS256** access tokens with required `sub`, `iat`, `exp`, `aud`, and
  `iss` claims; audience and issuer are validated on every decode.
- Usernames/passwords are never echoed in responses (`UserPublic` only).
- Registration returns a generic `409` for duplicate emails; login returns a
  generic `401` for both unknown email and wrong password (no user enumeration).
- Password rule: ≥ 8 chars, at least one letter and one digit, ≤ 72 bytes.
- CORS is an explicit origin/method/header allow-list with credentials disabled.
- API docs are disabled in production/staging. Production requires a strong
  `SECRET_KEY`, explicit CORS origins, and an HTTPS LLM base URL.
- Logout is stateless this phase; token revocation/refresh is future work.
- Uploads are validated by extension, size (5 MB cap), and `%PDF-` magic bytes
  before parsing; filenames are sanitized, MIME is forced to `application/pdf`,
  and empty/oversized/textless files are rejected.
- PDF parsing caps input at 50 pages and 2,000,000 extracted characters.
- Resume, job, match, roadmap, interview and evaluation reads are always
  filtered by `user_id`; other users' rows return **404** (not 403) to avoid
  leaking existence. Dashboard aggregation applies the same filter to every
  source table.
- The LLM API key stays in the backend `.env` — never in the browser. AI output
  is never trusted: it must validate against `JobAnalysisResult`, `RoadmapPlan`,
  `InterviewPlan` or `InterviewEvaluationDraft` before storage.
- A failed AI call returns **502** with a generic detail and writes nothing (no
  partial/corrupt rows); upstream details stay in server logs.
- The frontend sends tokens only on protected paths, clears them on `401`, adds
  a content security policy, disables duplicate form submissions, and caps
  interview answers at 10,000 characters.

## Why these choices

| Concern        | Choice                          | Reason                                              |
| -------------- | ------------------------------- | --------------------------------------------------- |
| API framework  | FastAPI                         | Typed, fast, auto OpenAPI docs                      |
| Validation     | Pydantic v2                     | Request/response + settings validation              |
| ORM            | SQLAlchemy 1.4                  | 2.x C-extensions blocked by Windows App Control here |
| Config         | pydantic-settings + `.env`      | 12-factor; secrets out of code                      |
| Frontend build | Vite                            | Fast HMR, first-class TS                            |
| Routing        | React Router 7                  | Standard SPA routing + protected routes             |
| PDF parsing    | pypdf                           | Pure Python; PyMuPDF blocked by App Control here    |
| LLM access     | httpx + JSON mode               | No vendor SDK; works with any OpenAI-compatible API |
| AI validation  | Pydantic contract + retry       | Untrusted model output never reaches storage        |
| Match scoring  | Pure Python, static relations   | Deterministic, explainable, no AI-generated score   |
| Roadmap output | Two normalised tables           | Progress/queries stay simple; JSON holds topic lists |
| Interview output | Two normalised tables         | Answers/progress stay queryable; questions remain ordered |
| Evaluation output | Two normalised tables        | Criteria/feedback stay queryable; one result per answer    |
| Dashboard output | Single read-only aggregate    | One authenticated request; no extra client-side data leaks |
| Readiness output | Fixed weights in Python       | Explainable components; no AI-generated placement score    |

## Implemented in Phase 5

- Skill-gap engine comparing `resumes.parsed_data` with `jobs` requirements.
- Reproducible 0–100 ranking, breakdown, gap lists and score explanation.
- Saved match rows with ownership-scoped retrieval.

## Implemented in Phase 6

- AI-recommended 7/14-day roadmaps driven by missing skills and study time.
- Strict `RoadmapPlan` validation, one repair retry and local curriculum fallback.
- Persisted daily checkpoints with server-derived progress percentage.

## Implemented in Phase 7

- Tailored 5–10 question mock interviews driven by resume, JD, projects and gaps.
- Strict `InterviewPlan` validation, one repair retry and local question fallback.
- Persisted text answers with server-derived progress and completion status.

## Implemented in Phase 8

- AI/local answer evaluation on four content-only criteria and `0`–`100` scores.
- Strict `InterviewEvaluationDraft` validation, one repair retry and heuristic fallback.
- Persisted overall feedback and per-answer criteria/model answers in two normalised tables.
- Idempotent evaluate/results endpoints with completed-session and ownership checks.
- React results page plus setup/session links to saved evaluations.

## Implemented in Phase 9

- Ownership-scoped, read-only dashboard aggregation with no AI calls.
- Deterministic resume completeness, latest match/interview scores and learned-skill count.
- Latest-match skill analysis and latest 7-day roadmap task progress.
- Interview attempt/score statistics, score trends and recent job activity.
- Responsive React dashboard using cards, SVG charts, progress bars and tables with
  loading, empty and error states.

## Implemented in Phase 10

- Deterministic five-component readiness score with explicit weights, clamped
  components, rounded total and named bands.
- Technical-preparation blend from all saved answer evaluations, including a
  problem-solving average when available.
- Target-skill frequency aggregation across all analyzed jobs with per-job
  deduplication, requirement-type counts and top-10 ordering.
- Dashboard UI additions for readiness donut/breakdown and target-skill bars.

## Implemented in Phase 11

- 163 backend tests and 12 frontend component tests covering auth, uploads,
  parsing, matching, scoring, roadmaps, interviews, dashboards and security.
- Hardened JWT claims, CORS, production settings, docs exposure, upload names,
  PDF resource limits, generic AI/health error details and frontend token flows.
- Added Vitest/React Testing Library setup and tests for the main user flows.

## Future extension points

- LLM orchestration improvements: rate limiting, caching, prompt versioning.
- Voice answers and transcription.
- OCR fallback for scanned resumes.
- Token refresh + revocation/blacklist.
- Alembic migrations once the schema grows.
