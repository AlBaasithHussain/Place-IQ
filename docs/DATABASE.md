# Database Documentation

## Engine and configuration

PrepPilot uses PostgreSQL in production and local development. SQLAlchemy 1.4.54 is pinned because SQLAlchemy 2.x compiled extensions are blocked by Windows Application Control on the original development machine.

Configuration is read from `DATABASE_URL` by `backend/app/core/config.py`.

Accepted formats:

```text
postgresql://USER:PASSWORD@HOST:5432/DBNAME
postgres://USER:PASSWORD@HOST:5432/DBNAME
```

The application normalizes `postgres://` to `postgresql://` so Render/Railway connection strings work without manual editing.

For hosted providers that require TLS, append the provider's SSL option, for example:

```text
postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

The SQLAlchemy engine uses `pool_pre_ping=True` and a short connection timeout. Database sessions are always closed by the `get_db()` dependency.

---

## Local PostgreSQL

A `docker-compose.yml` is provided at the repository root.

```powershell
docker compose up -d db
```

Local URL:

```text
postgresql://postgres:postgres@localhost:5432/placement_prep
```

These are development-only defaults. Do not use them in production.

---

## Table initialization

At application startup, `app/db/init_db.py` calls:

```python
Base.metadata.create_all(bind=engine)
```

This creates tables that do not exist. It does not migrate or alter existing tables.

Manual initialization:

```powershell
cd backend
python -m app.db.init_db
```

For future schema changes, introduce Alembic migrations and replace automatic `create_all()` in production with controlled migration steps.

---

## Tables

| Table | Purpose | Key columns |
| --- | --- | --- |
| `users` | Registered application users | `id`, `name`, `email` unique, `password_hash`, `created_at`, `updated_at` |
| `student_profiles` | Optional one-to-one student profile | `user_id` PK/FK, `college`, `degree`, `branch`, `graduation_year`, `target_role` |
| `resumes` | Uploaded PDF metadata and parsed content | `id`, `user_id`, `original_filename`, `file_size`, `mime_type`, `raw_text`, `parsed_data` |
| `jobs` | Analyzed job descriptions | `id`, `user_id`, `job_title`, `original_text`, skill JSON columns, `analysis_engine` |
| `match_analyses` | Deterministic resume-to-job match results | `id`, `user_id`, `resume_id`, `job_id`, `score`, `result` |
| `roadmaps` | Generated study plans | `id`, `user_id`, `resume_id`, `job_id`, `analysis_id`, `duration_days`, `hours_per_day`, `priority_skills`, `summary` |
| `roadmap_tasks` | Daily tasks belonging to a roadmap | `id`, `roadmap_id`, `day`, `title`, `priority`, `learning_topics`, `practice_tasks`, `mini_project`, `completed`, `completed_at` |
| `interviews` | Mock interview sessions | `id`, `user_id`, `resume_id`, `job_id`, `question_count`, `status`, `generation_engine`, `completed_at` |
| `interview_questions` | Questions and saved answers for a session | `id`, `interview_id`, `position`, `category`, `question`, `focus_skill`, `answer`, `answered_at` |
| `interview_evaluations` | One overall evaluation per completed interview | `id`, `interview_id` unique, `overall_score`, `overall_summary`, strengths/weaknesses JSON, `generation_engine` |
| `answer_evaluations` | Per-question evaluation criteria | `id`, `evaluation_id`, `question_id`, `position`, four criterion scores, feedback fields, `model_answer` |

---

## Relationships

```text
users 1──0..1 student_profiles
users 1──0..n resumes
users 1──0..n jobs
users 1──0..n match_analyses
users 1──0..n roadmaps
users 1──0..n interviews

resumes + jobs ──► match_analyses
match_analyses ──► roadmaps ──► roadmap_tasks
resumes + jobs ──► interviews ──► interview_questions
interviews ──► interview_evaluations ──► answer_evaluations
```

All user-owned tables use `ON DELETE CASCADE` from `users.id`. Child rows also cascade:

- deleting a roadmap deletes its tasks
- deleting an interview deletes its questions and evaluation
- deleting an evaluation deletes its answer evaluations

---

## Indexes and constraints

- Primary-key indexes exist on all `id` columns.
- `users.email` is unique and indexed.
- `user_id`, `resume_id`, `job_id`, `analysis_id`, `interview_id`, `evaluation_id`, and `question_id` foreign keys are indexed where queried.
- `interview_evaluations.interview_id` is unique to keep evaluation idempotent.
- `answer_evaluations` has a unique constraint on (`evaluation_id`, `position`).
- Timestamps use timezone-aware columns with server defaults where applicable.

---

## Ownership and data isolation

Every API query for user data filters by the authenticated `current_user.id`. Other users' rows return `404` instead of `403` to avoid leaking existence.

Dashboard, readiness, and target-skill aggregations apply the same ownership filter to every source table.

---

## Tests

Automated tests default to an in-memory SQLite database through `backend/tests/conftest.py`. This keeps tests fast and isolated.

To test against PostgreSQL:

```powershell
$env:TEST_DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/placement_prep_test"
cd backend
pytest
```

---

## Backup and restore

Use the hosting provider's backup feature where available. Manual backup/restore with PostgreSQL tools:

```powershell
pg_dump "$env:DATABASE_URL" --file="backup.sql"
psql "$env:DATABASE_URL" --file="backup.sql"
```

Keep backup files outside the repository and never commit them.

---

## Future improvements

- Add Alembic migrations for versioned schema changes.
- Add connection pool tuning for higher traffic.
- Add read replicas if dashboard aggregation becomes heavy.
- Add retention policies for raw resume text and evaluation data.
