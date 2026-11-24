"""Helpers shared by several routers."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..detection_engine import DEFAULT_WEIGHTS, EngineConfig
from ..models import Assignment, SimilarityResult, Submission, SystemSetting, User
from ..schemas import ResultSummary, SubmissionFileOut, SubmissionOut


def aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC so comparisons work on every backend."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def detection_settings(db: Session) -> EngineConfig:
    row = db.get(SystemSetting, "detection")
    return EngineConfig.from_dict(row.value if row else None)


def review_threshold_for(db: Session, assignment: Assignment) -> float:
    return assignment.review_threshold if assignment.review_threshold is not None else detection_settings(db).review_threshold


def submission_out(sub: Submission, include_files: bool = True) -> SubmissionOut:
    return SubmissionOut(
        id=sub.id, assignment_id=sub.assignment_id, assignment_title=sub.assignment.title if sub.assignment else None,
        student_id=sub.student_id, student_name=sub.student.full_name if sub.student else None,
        student_email=sub.student.email if sub.student else None, group_id=sub.group_id, version=sub.version,
        status=sub.status.value, submitted_at=sub.submitted_at, is_late=sub.is_late, duplicate_of_id=sub.duplicate_of_id,
        max_similarity=sub.max_similarity,
        files=[SubmissionFileOut.model_validate(f) for f in sub.files] if include_files else [],
    )


def party_label(sub: Submission, home_assignment_id: int) -> str:
    name = sub.student.full_name
    if sub.assignment_id != home_assignment_id:
        return f"{name} ({sub.assignment.title}, v{sub.version})"
    return name


def result_summary(r: SimilarityResult) -> ResultSummary:
    return ResultSummary(
        id=r.id, assignment_id=r.assignment_id, assignment_title=r.submission_a.assignment.title if r.submission_a.assignment else None,
        submission_a_id=r.submission_a_id, submission_b_id=r.submission_b_id,
        student_a=party_label(r.submission_a, r.assignment_id), student_b=party_label(r.submission_b, r.assignment_id),
        overall=r.overall, effective_score=r.effective_score, risk_level=r.risk_level, confidence_label=r.confidence_label,
        is_duplicate=r.is_duplicate, review_status=r.review_status.value, job_id=r.job_id,
    )


def latest_result_ids(assignment_ids: list[int]):
    """Sub-select of the newest result row per submission pair (re-runs keep reviewed rows from older jobs)."""
    return (
        select(func.max(SimilarityResult.id))
        .where(SimilarityResult.assignment_id.in_(assignment_ids))
        .group_by(SimilarityResult.submission_a_id, SimilarityResult.submission_b_id)
    )


def user_display(user: User | None) -> str | None:
    return user.full_name if user else None


def paginate(query_total: int, items: list, page: int, page_size: int) -> dict:
    return {"items": items, "total": query_total, "page": page, "page_size": page_size}


DEFAULT_DETECTION = {"weights": dict(DEFAULT_WEIGHTS), "review_threshold": 0.5, "high_threshold": 0.75}
