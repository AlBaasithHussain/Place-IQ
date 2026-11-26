# Screenshots

This repository is text-only; PNG captures should be added after deploying or running the app locally.

Recommended location:

```text
docs/screenshots/
```

Use descriptive names and avoid real personal data, API keys, or production tokens.

| Filename | Route | What to show |
| --- | --- | --- |
| `landing.png` | `/` | Hero, features, how-it-works sections |
| `dashboard.png` | `/dashboard` | Readiness score, target skills, charts and overview cards |
| `resumes.png` | `/resumes` | Upload form and saved resume list |
| `resume-detail.png` | `/resumes/{id}` | Parsed skills and extracted text |
| `jobs.png` | `/jobs` | JD input with character counter and sample button |
| `job-detail.png` | `/jobs/{id}` | Required/preferred skills and categories |
| `match-result.png` | `/analysis/{id}` | Score card, breakdown and skill table |
| `roadmap.png` | `/roadmaps/{id}` | Daily task cards and progress |
| `interview-session.png` | `/interviews/{id}` | Question flow and answer area |
| `interview-results.png` | `/interviews/{id}/results` | Overall score and criterion bars |

After adding images, reference them from the README with relative paths, for example:

```markdown
![Dashboard](docs/screenshots/dashboard.png)
```

Capture workflow:

```powershell
npm run dev
```

Open each route, sign in with a demo account, resize the browser to a desktop viewport, capture the PNG, and store it under `docs/screenshots/`.
