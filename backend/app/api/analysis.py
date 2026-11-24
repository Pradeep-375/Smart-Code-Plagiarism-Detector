from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..core.deps import get_assignment_for_staff, get_current_user, require_staff
from ..database import get_db
from ..detection_engine import ALGORITHMS, DISCLAIMER, DetectionEngine
from ..models import (
    AnalysisJob, Assignment, JobStatus, MatchedSegment, ReviewStatus, SimilarityResult, Submission, SubmissionStatus, User, utcnow,
)
from ..schemas import (
    AnalyzeIn, CompareIn, FileContentOut, JobOut, ResultDetail, ResultSummary, ReviewIn, SegmentOut, StudentFeedbackOut,
)
from ..services.analysis_service import build_files, load_engine_config
from ..services.audit import audit
from ..workers.tasks import dispatch_analysis
from .common import aware, latest_result_ids, party_label, result_summary, review_threshold_for, user_display

router = APIRouter(tags=["analysis"])


def _result_query(assignment_ids: list[int]):
    return (
        select(SimilarityResult)
        .where(SimilarityResult.id.in_(latest_result_ids(assignment_ids)))
        .options(
            joinedload(SimilarityResult.submission_a).joinedload(Submission.student),
            joinedload(SimilarityResult.submission_a).joinedload(Submission.assignment),
            joinedload(SimilarityResult.submission_b).joinedload(Submission.student),
            joinedload(SimilarityResult.submission_b).joinedload(Submission.assignment),
        )
    )


def _staff_result(db: Session, result_id: int, user: User) -> SimilarityResult:
    r = db.get(SimilarityResult, result_id)
    if not r:
        raise HTTPException(404, "Result not found")
    get_assignment_for_staff(db, r.assignment_id, user)
    return r


# ------------------------------------------------------------------ jobs
@router.post("/assignments/{assignment_id}/analyze", response_model=JobOut, status_code=202)
def start_analysis(assignment_id: int, request: Request, background: BackgroundTasks,
                   body: AnalyzeIn | None = None, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    body = body or AnalyzeIn()
    a = get_assignment_for_staff(db, assignment_id, user)
    if body.include_other_assignments and user.role_name != "admin":
        raise HTTPException(403, "Comparing against every assignment requires administrator permission")
    active = db.scalar(select(AnalysisJob).where(AnalysisJob.assignment_id == a.id, AnalysisJob.status.in_([JobStatus.queued, JobStatus.running])))
    if active:
        raise HTTPException(409, f"Analysis job {active.id} is already in progress for this assignment")
    n = db.scalar(select(func.count(func.distinct(Submission.student_id))).where(Submission.assignment_id == a.id)) or 0
    if n < 2 and not (body.include_history or body.include_other_assignments):
        raise HTTPException(400, "At least two students' submissions are needed (or enable history comparison)")
    config = {"weights": body.weights, "review_threshold": body.review_threshold, "high_threshold": body.high_threshold}
    if body.weights is not None:
        unknown = set(body.weights) - set(ALGORITHMS)
        if unknown or any(v < 0 for v in body.weights.values()):
            raise HTTPException(400, "Weights must reference known algorithms and be non-negative")
    job = AnalysisJob(assignment_id=a.id, requested_by=user.id, status=JobStatus.queued, include_history=body.include_history,
                      include_other_assignments=body.include_other_assignments, config=config, total_pairs=DetectionEngine.pair_count(n))
    db.add(job)
    for s in db.scalars(select(Submission).where(Submission.assignment_id == a.id)):
        s.status = SubmissionStatus.queued
    db.commit()
    db.refresh(job)
    audit(db, user.id, "analysis.start", request, "assignment", a.id, job_id=job.id, history=body.include_history, cross=body.include_other_assignments)
    dispatch_analysis(job.id, background)
    return job


@router.get("/analysis/jobs/{job_id}", response_model=JobOut)
def job_status(job_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    get_assignment_for_staff(db, job.assignment_id, user)
    return job


@router.get("/assignments/{assignment_id}/jobs", response_model=list[JobOut])
def list_jobs(assignment_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    get_assignment_for_staff(db, assignment_id, user)
    return db.scalars(select(AnalysisJob).where(AnalysisJob.assignment_id == assignment_id).order_by(AnalysisJob.id.desc()).limit(20)).all()


# ------------------------------------------------------------------ results
@router.get("/assignments/{assignment_id}/results")
def list_results(assignment_id: int, min_similarity: float = Query(0, ge=0, le=1), risk: str | None = None, review_status: str | None = None,
                 q: str = "", sort: str = "-overall", page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
                 user: User = Depends(require_staff), db: Session = Depends(get_db)):
    get_assignment_for_staff(db, assignment_id, user)
    # filters are applied to an id-only statement so counting never has to deal with eager-load options
    ids = select(SimilarityResult.id).where(SimilarityResult.id.in_(latest_result_ids([assignment_id])), SimilarityResult.overall >= min_similarity)
    if risk:
        ids = ids.where(SimilarityResult.risk_level == risk)
    if review_status:
        try:
            ids = ids.where(SimilarityResult.review_status == ReviewStatus(review_status))
        except ValueError:
            raise HTTPException(400, "Unknown review status")
    if q:
        like = f"%{q.lower()}%"
        matching_users = select(User.id).where(or_(func.lower(User.full_name).like(like), func.lower(User.email).like(like)))
        subs = select(Submission.id).where(Submission.student_id.in_(matching_users))
        ids = ids.where(or_(SimilarityResult.submission_a_id.in_(subs), SimilarityResult.submission_b_id.in_(subs)))
    total = db.scalar(select(func.count()).select_from(ids.subquery()))
    cols = {"overall": SimilarityResult.overall, "confidence": SimilarityResult.confidence, "review_status": SimilarityResult.review_status,
            "created_at": SimilarityResult.created_at}
    col = cols.get(sort.lstrip("-"), SimilarityResult.overall)
    stmt = (_result_query([assignment_id]).where(SimilarityResult.id.in_(ids))
            .order_by(col.desc() if sort.startswith("-") else col.asc(), SimilarityResult.id).limit(page_size).offset((page - 1) * page_size))
    rows = db.scalars(stmt).unique().all()
    return {"items": [result_summary(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/assignments/{assignment_id}/matrix")
def similarity_matrix(assignment_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    """Data for the similarity heat-map: students (latest submission each) and pairwise scores."""
    get_assignment_for_staff(db, assignment_id, user)
    rows = db.scalars(_result_query([assignment_id])).unique().all()
    inside = {r.submission_a_id: r.submission_a for r in rows if r.submission_a.assignment_id == assignment_id}
    inside.update({r.submission_b_id: r.submission_b for r in rows if r.submission_b.assignment_id == assignment_id})
    cells = [{"a": r.submission_a_id, "b": r.submission_b_id, "score": r.effective_score, "result_id": r.id}
             for r in rows if r.submission_a_id in inside and r.submission_b_id in inside]
    return {"submissions": [{"id": s.id, "label": s.student.full_name} for s in sorted(inside.values(), key=lambda s: s.student.full_name)], "cells": cells}


@router.get("/results/{result_id}", response_model=ResultDetail)
def result_detail(result_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    r = _staff_result(db, result_id, user)
    summary = result_summary(r)
    lang = r.submission_a.assignment.language_key
    reviewer = db.get(User, r.reviewed_by) if r.reviewed_by else None

    def files(sub: Submission) -> list[FileContentOut]:
        return [FileContentOut(id=f.id, filename=f.filename, language_key=f.language_key, content=f.content) for f in sub.files if f.language_key == lang]

    return ResultDetail(
        **summary.model_dump(), scores=r.scores, confidence=r.confidence, explanations=r.explanations, ml_probability=r.ml_probability,
        review_notes=r.review_notes, override_score=r.override_score, reviewed_at=r.reviewed_at, reviewer_name=user_display(reviewer),
        segments=[SegmentOut.model_validate(s) for s in r.segments], files_a=files(r.submission_a), files_b=files(r.submission_b), disclaimer=DISCLAIMER)


@router.patch("/results/{result_id}/review", response_model=ResultSummary)
def review_result(result_id: int, body: ReviewIn, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    """Manual faculty review: only a human can mark a pair confirmed; the score can be overridden with a note."""
    r = _staff_result(db, result_id, user)
    if body.review_status in ("confirmed", "dismissed") and len(body.notes.strip()) < 5:
        raise HTTPException(400, "Please record a short note explaining your decision")
    r.review_status, r.review_notes, r.override_score = ReviewStatus(body.review_status), body.notes.strip(), body.override_score
    r.reviewed_by, r.reviewed_at = user.id, utcnow()
    db.commit()
    audit(db, user.id, "result.review", request, "result", r.id, status=body.review_status, override=body.override_score)
    return result_summary(r)


@router.post("/analysis/compare", response_model=ResultDetail)
def ad_hoc_compare(body: CompareIn, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    """Compare two specific submissions immediately (not stored) - the result is returned in the same shape as stored ones."""
    if body.submission_a_id == body.submission_b_id:
        raise HTTPException(400, "Choose two different submissions")
    a, b = db.get(Submission, body.submission_a_id), db.get(Submission, body.submission_b_id)
    if not a or not b:
        raise HTTPException(404, "Submission not found")
    assignment = get_assignment_for_staff(db, a.assignment_id, user)
    if b.assignment_id != a.assignment_id:
        get_assignment_for_staff(db, b.assignment_id, user)
        if b.assignment.language_key != assignment.language_key:
            raise HTTPException(400, "Submissions use different languages")
    lang = assignment.language_key
    cfg = load_engine_config(db, assignment)
    template = [(x.filename, x.content) for x in assignment.reference_files] or None
    res = DetectionEngine(cfg).compare_files(build_files(a, lang), build_files(b, lang), lang, template=template)
    segs = [SegmentOut(id=i, a_file=s["a_file"], b_file=s["b_file"], a_start_line=s["a_start_line"], a_end_line=s["a_end_line"],
                       b_start_line=s["b_start_line"], b_end_line=s["b_end_line"], token_count=s["token_count"])
            for i, s in enumerate(res.segments)]
    audit(db, user.id, "analysis.compare", request, "assignment", assignment.id, a=a.id, b=b.id)

    def files(sub):
        return [FileContentOut(id=f.id, filename=f.filename, language_key=f.language_key, content=f.content) for f in sub.files if f.language_key == lang]

    return ResultDetail(
        id=0, assignment_id=assignment.id, assignment_title=assignment.title, submission_a_id=a.id, submission_b_id=b.id,
        student_a=party_label(a, assignment.id), student_b=party_label(b, assignment.id), overall=res.overall, effective_score=res.overall,
        risk_level=res.risk_level, confidence_label=res.confidence_label, is_duplicate=res.is_duplicate, review_status="pending", job_id=0,
        scores=res.scores, confidence=res.confidence, explanations=res.explanations, ml_probability=res.ml_probability, review_notes="",
        override_score=None, reviewed_at=None, reviewer_name=None, segments=segs, files_a=files(a), files_b=files(b), disclaimer=DISCLAIMER)


# ------------------------------------------------------------------ student feedback
@router.get("/submissions/{submission_id}/feedback", response_model=StudentFeedbackOut)
def student_feedback(submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """What a student may see: own status and, if the instructor enabled it, an anonymous similarity band."""
    sub = db.get(Submission, submission_id)
    if not sub or (user.role_name == "student" and sub.student_id != user.id):
        raise HTTPException(404, "Submission not found")
    assignment = sub.assignment
    visible = assignment.show_results_to_students and sub.status == SubmissionStatus.analyzed
    if not visible:
        msg = ("Your submission has been received." if sub.status != SubmissionStatus.analyzed
               else "Your submission was analysed. Your instructor has not released similarity feedback for this assignment.")
        return StudentFeedbackOut(submission_id=sub.id, status=sub.status.value, results_visible=False, message=msg)
    rows = db.scalars(select(SimilarityResult).where(
        SimilarityResult.id.in_(latest_result_ids([assignment.id])),
        or_(SimilarityResult.submission_a_id == sub.id, SimilarityResult.submission_b_id == sub.id),
        SimilarityResult.review_status != ReviewStatus.dismissed)).all()
    best = max((r.effective_score for r in rows), default=0.0)
    cfg_review = review_threshold_for(db, assignment)
    high = assignment.high_threshold if assignment.high_threshold is not None else 0.75
    band = "high" if best >= high else "review" if best >= cfg_review else "low"
    msg = {"low": "No notable similarity to other submissions was found.",
           "review": "Some of your code is similar to other work. This is an automated indicator only; your instructor may review it.",
           "high": "A large part of your code is similar to other work. Your instructor will review it before any decision is made."}[band]
    return StudentFeedbackOut(submission_id=sub.id, status=sub.status.value, results_visible=True, max_similarity=round(best, 4), band=band, message=msg)
