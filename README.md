# Smart Code Plagiarism Detection System

A full-stack platform for faculty to detect **suspicious code similarity** in student programming assignments, and for students to see their own submission status.
Supports Python, Java, C, C++, JavaScript and TypeScript.

> **Similarity is not proof of plagiarism.** The system reports similarity and the evidence behind it. Every flagged pair is `pending` until a faculty member reviews it; nothing is ever confirmed automatically. Template/boilerplate code, common algorithms and short programs naturally score high.

## Contents
1. [Features](#features) · 2. [Architecture](#architecture) · 3. [Project structure](#project-structure) · 4. [Quick start](#quick-start) · 5. [Configuration](#configuration) · 6. [Testing](#testing) · 7. [Detection engine](#detection-engine) · 8. [Security](#security) · 9. [Deployment](#deployment) · 10. [Verification status](#verification-status) · 11. [Limitations](#limitations)

## Features
- **Roles & RBAC** – admin, faculty, student. Students only ever see their own submissions and (if the instructor allows) their own similarity status, never peers' identities or code.
- **Detection** – exact, token (greedy string tiling), lexical, AST, TF-IDF/cosine, winnowing fingerprints, structural (control-flow) and transformation analysis (renaming, reordering, reformatting, loop/operator rewrites), combined with admin-configurable weights and thresholds, plus an optional small logistic-regression layer.
- **Explanations** – each result lists the detected transformations, matched code segments, per-algorithm scores and a measurement-confidence indicator.
- **Comparison UI** – side-by-side Monaco editors (desktop) / stacked line view (mobile), match navigation, algorithm breakdown, review form (dismiss / flag / confirm + notes), PDF report.
- **Assignments** – CRUD, deadlines, groups, reference/template files excluded from scoring, per-assignment thresholds, student visibility toggle.
- **Secure upload** – extension allow-list, size/count limits, ZIP bomb and path-traversal protection, UTF-8 validation. Uploaded code is only ever read as text, never executed.
- **Analytics** – role-specific dashboards computed from the database (no hard-coded numbers), similarity heatmap/matrix, distributions, CSV and PDF export.
- **Operations** – audit logs, in-app notifications (optional e-mail), background analysis with live progress (Celery, with a built-in fallback), rate limiting, security headers.
- **UI** – dark mode, installable PWA, responsive layouts with a separately designed mobile experience (bottom navigation, card-style tables).

## Architecture
```
 React SPA (Vite, TS, Tailwind)  ──HTTPS/JSON + JWT──▶  FastAPI  ──▶  PostgreSQL
                                                         │   └────▶  Redis ──▶ Celery worker(s)
                                                         └─ detection_engine (pure-Python, no network, no code execution)
```
The detection engine is a self-contained package (`backend/app/detection_engine`) with no web or database dependencies, so it can be tested and reused on its own. See [docs/architecture.md](docs/architecture.md).

## Project structure
```
backend/
  app/
    api/                routers: auth, users, admin, assignments, submissions, analysis, reports, dashboard, notifications
    core/               config, security (JWT/bcrypt), deps (RBAC), rate limiting
    database/ models/ schemas/ services/ workers/ reports/
    detection_engine/   languages, tokenizer, normalizer, structure, algorithms, scoring, engine, facade, ml, samples
  migrations/           Alembic
  scripts/              evaluate_engine.py, train_ml.py
  tests/                engine, quality (precision/recall/F1), upload, reports, api/
frontend/
  src/{pages,components,layouts,contexts,hooks,services,utils,types}
  tests/{unit,e2e}
docs/                   architecture, database, API, algorithms, deployment, testing, troubleshooting, evaluation_report
docker-compose.yml  .env.example
```

## Quick start

### A. Local development (no Docker, no Redis, SQLite)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
export SEED_ADMIN_EMAIL=admin@example.com SEED_ADMIN_PASSWORD='ChangeMe123'   # first administrator
export SEED_DEMO_DATA=true                                                   # optional demo class (accounts use the same password)
uvicorn app.main:app --reload           # http://localhost:8000/docs
```
```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173 (proxies /api to :8000)
```
Demo accounts (only when `SEED_DEMO_DATA=true`): `faculty@example.com`, `student1@example.com` … `student6@example.com`, plus the admin above.

### B. Docker (PostgreSQL + Redis + Celery)
```bash
cp .env.example .env     # fill SECRET_KEY, POSTGRES_PASSWORD, SEED_ADMIN_PASSWORD
docker compose up --build
# web: http://localhost:8080
```

## Configuration
Environment variables (see `backend/app/core/config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | – (required in production) | JWT signing key |
| `DATABASE_URL` | `sqlite:///./dev.db` | use `postgresql://…` in production |
| `USE_CELERY` / `REDIS_URL` | `false` / `redis://localhost:6379/0` | background queue; when false, FastAPI BackgroundTasks run the analysis |
| `CORS_ORIGINS`, `FRONTEND_URL` | `http://localhost:5173` | allowed origins / links in e-mails |
| `STORAGE_DIR` | `./storage` | uploaded files |
| `MAX_UPLOAD_BYTES`, `MAX_ZIP_BYTES`, `MAX_ZIP_FILES`, `MAX_ZIP_UNCOMPRESSED_BYTES` | 2 MB / 10 MB / 100 / 20 MB | upload limits |
| `RATE_LIMIT_PER_MINUTE`, `AUTH_RATE_LIMIT_PER_MINUTE` | 120 / 10 | per-IP limits |
| `SMTP_*` | empty | optional e-mail (password reset, notifications) |
| `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD`, `SEED_DEMO_DATA` | – | first admin / demo data. No default credentials exist. |
| `FACULTY_REGISTRATION_CODE` | *(empty)* | access code that lets faculty self-register on the Register page. Empty = faculty self-registration disabled (admins can still create faculty). |

Detection weights and thresholds are editable by admins in **Profile → System configuration** (stored in the database); assignments can override the thresholds.
Frontend: `VITE_API_URL` (empty = same origin `/api/v1`).

## Testing
```bash
cd backend && pytest                  # engine, quality, upload, reports, and API tests
python scripts/evaluate_engine.py     # regenerates docs/evaluation_report.md
python scripts/train_ml.py            # retrains the optional ML layer
cd frontend && npm test               # vitest unit/component tests
cd frontend && npx playwright install && npm run test:e2e   # responsive checks (mobile/tablet/desktop)
```
Details in [docs/testing.md](docs/testing.md).

## Detection engine
Eight algorithms (scores 0–1) are combined as a weighted mean (defaults: exact .08, token .17, lexical .10, AST .15, TF-IDF .10, winnowing .18, structural .10, transformation .12). Levels: **low** < 50 %, **medium** ≥ 50 %, **high** ≥ 75 % (configurable). Full description in [docs/algorithms.md](docs/algorithms.md); measured results in [docs/evaluation_report.md](docs/evaluation_report.md).

On the bundled synthetic benchmark the default configuration has precision/recall/F1 = 1.0 with no false positives; hard cases (hand-restructured copies) score ~57–67 % and independent solutions of the same task ≤ 34 %. **That benchmark is small and synthetic – treat it as a regression test, not as real-world accuracy.** Calibrate thresholds on your own course data.

## Accounts and registration
| Role | How the account is created |
|---|---|
| Student | Register page → *Register as Student* (open to anyone) |
| Faculty | Register page → *Register as Faculty* with the `FACULTY_REGISTRATION_CODE`, **or** an admin creates it (Users page / `POST /users`) |
| Admin | Never via public registration (`role: "admin"` is rejected). First admin = `SEED_ADMIN_*` at first start; more admins = an existing admin, or `python backend/scripts/create_admin.py --email you@example.com` (prompts for the password; add `--promote` to upgrade an existing account) |

The role is always stored in and read back from the database; tokens carry a role claim but every request re-checks the user's current role in the DB.

## Security
bcrypt password hashing · JWT bearer tokens with expiry · role checks on every route (ownership checks for faculty/students) · Pydantic validation · parameterised SQL via SQLAlchemy · upload allow-list, size limits, ZIP-bomb/path-traversal/symlink defence, no execution of uploads · rate limiting (stricter on auth) · security headers · CORS allow-list · audit log · secrets only via environment (production refuses to start with the default key) · password-reset tokens are single-use and hashed.
Known trade-offs: the token is kept in `localStorage` (simple, but XSS-sensitive – consider httpOnly cookies for high-security deployments), and the rate limiter is in-process (use a shared limiter / reverse-proxy limits when running several replicas).

## Deployment
See [docs/deployment.md](docs/deployment.md) (Vercel/Netlify for the SPA, Render/Railway/any container host for the API and worker, managed PostgreSQL and Redis).

### Docker
```bash
cp .env.example .env
# Fill SECRET_KEY, POSTGRES_PASSWORD, and SEED_ADMIN_PASSWORD
docker compose up --build
```
Open http://localhost:8080. PostgreSQL data and uploaded files are stored in Docker volumes.

### Render and Vercel
- Render: deploy the repository using `render.yaml`; configure a Render PostgreSQL database and secure admin environment variables.
- Vercel: use `frontend` as the root directory, `npm run build` as the build command, `dist` as the output directory, and set `VITE_API_BASE_URL` to the Render service origin or `/api/v1` base.

## Verification status
Be aware of what has and has not been executed:
- ✅ **Executed and passing**: detection-engine unit tests, quality/evaluation tests, upload-safety tests and PDF-report tests (61 tests).
- ⚠️ **Written but not executed in the build environment** (no network to install dependencies): the FastAPI application, SQLAlchemy models, Alembic migration, Celery tasks, the API test suite (`backend/tests/api`), the whole React frontend (not type-checked or built), the frontend tests and the Docker files. They were reviewed and syntax-checked, but expect to fix small issues on first run (`pip install`, `pytest`, `npm install`, `npm run build`).

## Limitations
- Similarity analysis is heuristic; clever restructuring or tiny programs can evade or inflate scores.
- Languages other than Python use a pseudo-AST built from brackets/keywords, not a full parser.
- Pairwise comparison is O(n²); an inverted-index prefilter kicks in above 150 submissions, but very large classes should run analysis on Celery workers.
- E-mail is optional and untested against a live SMTP server.
