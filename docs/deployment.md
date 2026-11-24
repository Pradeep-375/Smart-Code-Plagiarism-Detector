# Deployment

## Environment
Set at least: `ENVIRONMENT=production`, `SECRET_KEY` (≥32 random chars), `DATABASE_URL`, `CORS_ORIGINS` (your frontend origin), `FRONTEND_URL`, `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` (first run only), and for queues `USE_CELERY=true` + `REDIS_URL`.

## Docker Compose (single host)
`cp .env.example .env`, fill values, `docker compose up -d --build`. The backend container runs `alembic upgrade head` on start. Put a TLS-terminating reverse proxy (Caddy/Traefik/nginx) in front of port 8080.

## Frontend on Vercel or Netlify
Root `frontend/`, build `npm run build`, output `dist`. Set `VITE_API_URL=https://<api-host>/api/v1`. `vercel.json` / `netlify.toml` already contain the SPA rewrite and security headers. Add the site origin to the API's `CORS_ORIGINS`.

## Backend on Render (or Railway/Fly)
1. Create a managed PostgreSQL instance and a Redis instance.
2. Web service from `backend/` (Docker). Env: variables above, `DATABASE_URL` from the managed database.
3. Background worker from the same image with command `celery -A app.workers.celery_app.celery_app worker --loglevel=info`.
4. Attach a persistent disk at `STORAGE_DIR` (or run a single instance) so web and worker share uploads; for multiple hosts move uploads to object storage.
5. Health check path: `/api/v1/health`.

## Operations
Back up PostgreSQL and the storage volume. Rotate `SECRET_KEY` only with a planned logout of all users. Review `/admin/audit-logs` regularly.
