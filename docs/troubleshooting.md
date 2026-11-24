# Troubleshooting
- **App refuses to start in production** – `SECRET_KEY` is missing/default, or `SEED_ADMIN_PASSWORD` is not set for the first run.
- **CORS errors** – add the exact frontend origin to `CORS_ORIGINS`.
- **Analysis stays "queued"** – with `USE_CELERY=true` a worker must be running and reach Redis; set `USE_CELERY=false` for local use.
- **Upload rejected** – check extension (.py .java .c .cpp .js .ts and .zip), size limits and that the language is enabled for the assignment.
- **429 Too Many Requests** – rate limit hit; adjust `RATE_LIMIT_PER_MINUTE`.
- **Frontend cannot reach API** – set `VITE_API_URL` at build time or proxy `/api` (nginx/Vite).
- **Many false positives** – raise the assignment's review threshold, add the instructor template as a reference file.
