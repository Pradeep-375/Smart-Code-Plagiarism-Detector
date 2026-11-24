# API reference
Base path `/api/v1`. Interactive docs at `/docs` (disabled when `ENVIRONMENT=production`). Auth: `Authorization: Bearer <token>`.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register` (students only), `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/change-password`; `GET/PATCH /auth/me` |
| Users (admin) | `GET/POST /users`, `PATCH/DELETE /users/{id}` |
| Assignments | `GET/POST /assignments`, `GET/PATCH/DELETE /assignments/{id}`; `/assignments/{id}/groups`, `/reference-files` |
| Submissions | `POST /assignments/{id}/submissions` (multipart `files`, optional `student_id`, `group_id`), `GET /assignments/{id}/submissions`, `GET /submissions/mine`, `GET /submissions/{id}`, `GET /submissions/{id}/files/{file_id}`, `DELETE /submissions/{id}` |
| Analysis | `POST /assignments/{id}/analyze`, `GET /analysis/jobs/{id}`, `GET /assignments/{id}/jobs`, `/results`, `/matrix`; `GET /results/{id}`; `PATCH /results/{id}/review`; `POST /analysis/compare` (ad-hoc pair); `GET /submissions/{id}/feedback` (student) |
| Reports | `GET /results/{id}/report.pdf`, `/assignments/{id}/report.pdf`, `/assignments/{id}/export.csv`, `/assignments/{id}/reports`, `/reports/{id}/download` |
| Dashboard | `GET /dashboard/admin|faculty|student` |
| Notifications | `GET /notifications`, `POST /notifications/{id}/read`, `/notifications/read-all` |
| Admin | `GET /languages`, `/admin/languages`, `GET/PUT /admin/settings/detection`, `GET /admin/audit-logs` |
| Health | `GET /health` |

Errors use `{"detail": ...}` with standard HTTP codes (400 validation of business rules, 401, 403, 404, 413, 422, 429).
Password rule: 8–128 characters with at least one letter and one digit.
