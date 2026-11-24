# Architecture

**Layers**: React SPA → FastAPI (routers → services → SQLAlchemy models) → PostgreSQL; long-running analysis goes to Celery (Redis broker) or, in development, FastAPI `BackgroundTasks`.

**Request flow (analysis)**: faculty `POST /assignments/{id}/analyze` → an `AnalysisJob` row (`queued`) is created → worker loads submissions and reference files, calls `DetectionEngine.compare_batch` with progress callbacks (job `progress` updated) → `SimilarityResult` + `MatchedSegment` rows are written → job `completed`; the UI polls `/assignments/{id}/jobs` every 1.5 s while a job is active. Re-running analysis keeps history; the UI shows the latest result per pair.

**Detection engine** is import-free of web/DB code: `languages → tokenizer → normalizer → structure → algorithms → scoring → engine → facade`. The facade converts to the API's 0–1 fractions and adds the optional ML probability.

**Authorization**: `core/deps.py` provides `get_current_user`, `require_staff`, `require_admin`. Faculty are restricted to assignments they own; students to their own submissions. Student feedback endpoints return only status/level and never peers' identities or code.

**Frontend**: route-level code splitting (lazy pages), context providers for auth/theme/toasts, a typed axios client, `DataTable` rendering cards under 768 px, bottom navigation + drawer on mobile, Monaco on ≥1024 px (a lightweight line list otherwise).
