from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_staff
from ..database import get_db
from ..models import AnalysisJob, Assignment, JobStatus, ReviewStatus, SimilarityResult, Submission, SubmissionStatus, User, utcnow
from .common import aware, detection_settings, latest_result_ids, result_summary
from .analysis import _result_query

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _staff_dashboard(db: Session, user: User, days: int, language: str | None, assignment_id: int | None) -> dict:
    scope = select(Assignment)
    if user.role_name == "faculty":
        scope = scope.where(Assignment.created_by == user.id)
    if language:
        scope = scope.where(Assignment.language_key == language)
    if assignment_id:
        scope = scope.where(Assignment.id == assignment_id)
    assignments = db.scalars(scope).all()
    ids = [a.id for a in assignments] or [-1]
    since = utcnow() - timedelta(days=days)
    default_review = detection_settings(db).review_threshold

    subs = db.scalars(select(Submission).where(Submission.assignment_id.in_(ids), Submission.submitted_at >= since)).all()
    results = db.scalars(_result_query(ids)).unique().all()
    threshold = {a.id: (a.review_threshold if a.review_threshold is not None else default_review) for a in assignments}
    flagged = [r for r in results if r.effective_score >= threshold.get(r.assignment_id, default_review) and r.review_status == ReviewStatus.pending]

    by_lang = Counter()
    lang_of = {a.id: a.language_key for a in assignments}
    for s in subs:
        by_lang[lang_of[s.assignment_id]] += 1

    monthly: dict[str, int] = defaultdict(int)
    for s in subs:
        d = aware(s.submitted_at)
        monthly[f"{d.year}-{d.month:02d}"] += 1

    per_assignment = []
    for a in assignments:
        rs = [r for r in results if r.assignment_id == a.id]
        n = db.scalar(select(func.count()).select_from(Submission).where(Submission.assignment_id == a.id)) or 0
        per_assignment.append({
            "assignment_id": a.id, "title": a.title, "language": a.language_key, "submissions": n, "pairs": len(rs),
            "average_similarity": round(sum(r.effective_score for r in rs) / len(rs), 4) if rs else 0.0,
            "flagged": sum(1 for r in rs if r.effective_score >= threshold[a.id]),
        })

    job_q = select(func.count()).select_from(AnalysisJob).where(AnalysisJob.assignment_id.in_(ids))
    data = {
        "totals": {
            "assignments": len(assignments),
            "submissions": db.scalar(select(func.count()).select_from(Submission).where(Submission.assignment_id.in_(ids))) or 0,
            "completed_analyses": db.scalar(job_q.where(AnalysisJob.status == JobStatus.completed)) or 0,
            "pending_analyses": db.scalar(job_q.where(AnalysisJob.status.in_([JobStatus.queued, JobStatus.running]))) or 0,
            "unanalyzed_submissions": db.scalar(select(func.count()).select_from(Submission).where(
                Submission.assignment_id.in_(ids), Submission.status.in_([SubmissionStatus.uploaded, SubmissionStatus.queued]))) or 0,
            "average_similarity": round(sum(r.effective_score for r in results) / len(results), 4) if results else 0.0,
            "high_similarity_cases": len(flagged),
        },
        "language_distribution": [{"language": k, "count": v} for k, v in sorted(by_lang.items())],
        "monthly_submissions": [{"month": k, "count": v} for k, v in sorted(monthly.items())],
        "assignment_stats": sorted(per_assignment, key=lambda x: -x["flagged"])[:15],
        "cases_for_review": [result_summary(r).model_dump() for r in sorted(flagged, key=lambda r: -r.effective_score)[:8]],
        "filters": {"days": days, "language": language, "assignment_id": assignment_id},
    }
    if user.role_name == "admin":
        data["totals"]["users"] = db.scalar(select(func.count()).select_from(User)) or 0
        counts = Counter(u.role.name for u in db.scalars(select(User)).unique())
        data["users_by_role"] = [{"role": k, "count": v} for k, v in sorted(counts.items())]
    return data


@router.get("/admin")
def admin_dashboard(days: int = Query(365, ge=1, le=3650), language: str | None = None, assignment_id: int | None = None,
                    user: User = Depends(require_staff), db: Session = Depends(get_db)):
    if user.role_name != "admin":
        raise HTTPException(403, "Administrator access required")
    return _staff_dashboard(db, user, days, language, assignment_id)


@router.get("/faculty")
def faculty_dashboard(days: int = Query(365, ge=1, le=3650), language: str | None = None, assignment_id: int | None = None,
                      user: User = Depends(require_staff), db: Session = Depends(get_db)):
    return _staff_dashboard(db, user, days, language, assignment_id)


@router.get("/student")
def student_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mine = db.scalars(select(Submission).where(Submission.student_id == user.id).order_by(Submission.submitted_at.desc())).unique().all()
    submitted_ids = {s.assignment_id for s in mine}
    open_assignments = db.scalars(select(Assignment).where(Assignment.is_published.is_(True)).order_by(Assignment.deadline.is_(None), Assignment.deadline)).all()
    now = utcnow()
    todo = []
    for a in open_assignments:
        if a.id in submitted_ids:
            continue
        d = aware(a.deadline)
        todo.append({"id": a.id, "title": a.title, "language_key": a.language_key, "deadline": a.deadline, "overdue": bool(d and d < now)})
    status_counts = Counter(s.status.value for s in mine)
    return {
        "totals": {"submissions": len(mine), "assignments_to_do": len(todo), "late_submissions": sum(1 for s in mine if s.is_late),
                   "analyzed": status_counts.get("analyzed", 0), "pending": sum(v for k, v in status_counts.items() if k != "analyzed")},
        "status_distribution": [{"status": k, "count": v} for k, v in sorted(status_counts.items())],
        "todo": todo[:10],
        "recent": [{"id": s.id, "assignment_id": s.assignment_id, "assignment_title": s.assignment.title, "version": s.version,
                    "status": s.status.value, "submitted_at": s.submitted_at, "is_late": s.is_late} for s in mine[:8]],
    }
