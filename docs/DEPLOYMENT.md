# Deployment Guide

This guide prepares PrepPilot for GitHub and production deployment:

- Frontend: Vercel
- Backend: Render or Railway
- Database: hosted PostgreSQL (Render, Railway, Neon, Supabase, or equivalent)

No real secrets are stored in this repository. Only `.env.example` files are committed.

---

## 1. Deployment topology

```text
Browser
  │  HTTPS
  ▼
Vercel (React + Vite static build)
  │  Authorization: Bearer <JWT>
  │  VITE_API_BASE_URL = backend origin
  ▼
Render/Railway (FastAPI + Uvicorn)
  │  SQLAlchemy ORM
  │  DATABASE_URL = hosted PostgreSQL URL
  ▼
PostgreSQL hosting provider
```

The frontend never receives `DATABASE_URL`, `SECRET_KEY`, or `LLM_API_KEY`.

---

## 2. GitHub commands

Run these from the repository root after reviewing `git status` and confirming no `.env` files are staged.

```powershell
git status
git add .
git commit -m "Prepare PrepPilot for GitHub and deployment"
git branch -M main
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

If a remote already exists, replace `git remote add` with:

```powershell
git remote set-url origin https://github.com/OWNER/REPOSITORY.git
```

Replace `OWNER` and `REPOSITORY` with your GitHub values. Do not put tokens in the URL.

---

## 3. Environment variables

### Backend

Set these on Render/Railway. The application reads them through `pydantic-settings`.

| Variable | Required | Example / value | Notes |
| --- | --- | --- | --- |
| `ENVIRONMENT` | Yes | `production` | Disables `/docs`, `/redoc`, and `/api/v1/openapi.json`. |
| `PROJECT_NAME` | No | `Placement Prep API` | Used in the root response. |
| `API_V1_STR` | No | `/api/v1` | API prefix. |
| `BACKEND_CORS_ORIGINS` | Yes | `https://preppilot.vercel.app` | Exact frontend origin(s), comma-separated. No `*`. |
| `DATABASE_URL` | Yes | `postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require` | Use the hosting provider's connection string. `postgres://` is normalized automatically. |
| `SECRET_KEY` | Yes | generated random value | At least 32 characters. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ALGORITHM` | Yes | `HS256` | Production supports HS256 only. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Must be between 1 and 1440. |
| `LLM_PROVIDER` | No | `openai` | Informational only. |
| `LLM_API_KEY` | No | provider key | Optional. Leave unset to use deterministic heuristic fallbacks. |
| `LLM_MODEL` | No | `gpt-4o-mini` | Provider model name. |
| `LLM_BASE_URL` | No | `https://api.openai.com/v1` | Must be HTTPS outside localhost. |
| `LLM_TIMEOUT_SECONDS` | No | `30` | Must be between 1 and 300. |

Generate `SECRET_KEY` locally and paste only into the hosting provider dashboard:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### Frontend

Set this in the Vercel project settings.

| Variable | Required | Example | Notes |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | Yes | `https://preppilot-api.onrender.com` | Full backend origin, no trailing slash needed. Vite embeds this at build time. |

After changing `VITE_API_BASE_URL`, rebuild/redeploy the frontend.

---

## 4. Production CORS

Production CORS is intentionally strict:

- Origins: only `BACKEND_CORS_ORIGINS`
- Methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`
- Headers: `Authorization`, `Content-Type`
- Credentials: disabled

Example for a Vercel app plus custom domain:

```text
BACKEND_CORS_ORIGINS=https://preppilot.vercel.app,https://preppilot.example.com
```

Do not use `*`. Do not include a path or trailing slash. If the frontend domain changes, update this variable and redeploy the backend.

---

## 5. PostgreSQL hosting

Use a managed PostgreSQL provider. Recommended options:

- Render PostgreSQL
- Railway PostgreSQL
- Neon
- Supabase

Connection string format:

```text
postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```

Important notes:

- Use the provider's pooler/external URL when available.
- Keep the database private if the platform supports private networking.
- The app normalizes `postgres://` to `postgresql://` automatically.
- Tables are created on startup with SQLAlchemy `create_all()`. This creates missing tables but does not perform schema migrations.
- For future schema changes, add Alembic migrations before altering existing columns.

See [DATABASE.md](DATABASE.md) for the full schema and operational notes.

---

## 6. Frontend deployment to Vercel

### Project settings

| Setting | Value |
| --- | --- |
| Repository | your GitHub repository |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment Variable | `VITE_API_BASE_URL=https://YOUR-BACKEND-ORIGIN` |

`frontend/vercel.json` already contains the SPA rewrite to `index.html`.

### Local production build verification

```powershell
cd frontend
npm ci
npm test
npm run typecheck
npm run build
```

---

## 7. Backend deployment to Render

A Blueprint is provided at `backend/render.yaml`.

### Option A: Blueprint

1. Create a new Render Blueprint from the GitHub repository.
2. Select `backend/render.yaml`.
3. Replace the placeholder `BACKEND_CORS_ORIGINS` value with the real Vercel origin.
4. Fill in `SECRET_KEY` when Render prompts for it.
5. Deploy the PostgreSQL database and web service.

### Option B: Dashboard

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/v1/health` |
| Plan | Starter or higher |

Set all backend environment variables from section 3.

### Useful commands

Build:

```powershell
pip install -r requirements.txt
```

Start:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 8. Backend deployment to Railway

A `railway.json` is provided in `backend/`.

1. Create a Railway project from the GitHub repository.
2. Add a PostgreSQL service.
3. Set the service Root Directory to `backend`.
4. Railway will use `backend/railway.json`.
5. Set the backend environment variables from section 3.
6. Copy `DATABASE_URL` from the PostgreSQL service into the web service.
7. Generate a Railway domain.
8. Set `BACKEND_CORS_ORIGINS` to the Vercel frontend origin.
9. Set `VITE_API_BASE_URL` in Vercel to the Railway backend origin and redeploy the frontend.

Start command used by the config:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 9. Deployment order

1. Create PostgreSQL hosting and obtain `DATABASE_URL`.
2. Deploy backend to Render or Railway.
3. Confirm `GET /api/v1/health` returns `200`.
4. Confirm `GET /api/v1/health/db` reports a healthy database.
5. Deploy frontend to Vercel with `VITE_API_BASE_URL`.
6. Update backend `BACKEND_CORS_ORIGINS` with the Vercel origin.
7. Redeploy backend.
8. Register a test account and complete the main user flow.

---

## 10. Build and start command reference

| Component | Build command | Start/output command |
| --- | --- | --- |
| Frontend (Vercel) | `npm ci && npm run build` | Vercel static output from `dist` |
| Backend (Render/Railway) | `pip install -r requirements.txt` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Database | managed hosting | `DATABASE_URL` injected into backend |

---

## 11. Final production checklist

After deployment, verify all items:

- [ ] GitHub repository contains no `.env`, API keys, passwords, or real secrets.
- [ ] `backend/.env.example` and `frontend/.env.example` are committed; real `.env` files are not.
- [ ] PostgreSQL is reachable from the backend.
- [ ] `GET /api/v1/health` returns `200`.
- [ ] `GET /api/v1/health/db` reports database health.
- [ ] Required tables exist: `users`, `student_profiles`, `resumes`, `jobs`, `match_analyses`, `roadmaps`, `roadmap_tasks`, `interviews`, `interview_questions`, `interview_evaluations`, `answer_evaluations`.
- [ ] `ENVIRONMENT=production`.
- [ ] Interactive docs are disabled in production (`/docs` returns `404`).
- [ ] `SECRET_KEY` is strong and stored only in the hosting provider.
- [ ] `DATABASE_URL` uses the hosted PostgreSQL connection string and TLS where available.
- [ ] `BACKEND_CORS_ORIGINS` contains the exact Vercel origin and no wildcard.
- [ ] `VITE_API_BASE_URL` points to the deployed backend origin.
- [ ] Browser login/register works without CORS errors.
- [ ] Resume upload accepts PDF and rejects invalid files.
- [ ] JD analysis works with AI configured or heuristic fallback.
- [ ] Match score, roadmap, interview, evaluation, and dashboard flows work end-to-end.
- [ ] `401` responses clear the frontend token and redirect to `/login`.
- [ ] Automated tests pass before each deploy.
- [ ] Database backups are enabled on the hosting provider.
- [ ] Logs do not contain secrets or upstream API keys.
