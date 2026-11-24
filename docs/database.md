# Database design

Tables (see `backend/app/models/models.py`): `roles`, `users`, `programming_languages`, `assignments`, `assignment_groups` (+ `group_members`), `reference_files`, `submissions`, `submission_files` (content, sha256, language), `code_fingerprints`, `analysis_jobs`, `similarity_results` (per-algorithm scores JSON, overall, risk level, confidence, explanations, ML probability, review status/notes/reviewer), `matched_segments`, `notifications`, `audit_logs`, `reports`, `password_reset_tokens`, `system_settings` (key/value JSON, e.g. detection weights).

Key relations: assignment 1–N submissions 1–N files; assignment 1–N jobs 1–N results (each result references two submissions); result 1–N segments.
Indexes exist on foreign keys and on frequently filtered columns (assignment, overall score, review status, user email, audit action/time). Alembic migrations live in `backend/migrations` (`alembic upgrade head`); SQLite development databases are created automatically.
