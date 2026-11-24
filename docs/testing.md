# Testing

| Suite | Location | Command |
|---|---|---|
| Detection engine unit tests | `backend/tests/test_detection_engine.py` | `pytest` |
| Detection quality (precision/recall/F1, false positives, hard negatives) | `backend/tests/test_detection_quality.py` | `pytest` |
| Upload safety (ZIP bomb, traversal, extension, size) | `backend/tests/test_file_upload.py` | `pytest` |
| PDF reports | `backend/tests/test_reports.py` | `pytest` |
| API / RBAC / integration flow | `backend/tests/api/` | `pytest` (needs `requirements-dev.txt`) |
| Frontend unit/component | `frontend/tests/unit` | `npm test` |
| Responsive (mobile/tablet/desktop) | `frontend/tests/e2e` | `npm run test:e2e` |

API tests use a temporary SQLite database. To run against PostgreSQL set `DATABASE_URL` before `pytest`.
`python scripts/evaluate_engine.py` regenerates `docs/evaluation_report.md` (confusion matrix, per-category scores, threshold sweep, nearest false positives/negatives). The evaluation corpus is synthetic and small; see the caveat in the report.
