"""Runs plagiarism analysis jobs: gathers code, calls the engine, persists results.

Executed either by a Celery worker or by FastAPI BackgroundTasks (see workers/tasks.py).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..detection_engine import DetectionConfig, DetectionEngine, EngineConfig, prepare_file
from ..models import (
    AnalysisJob, Assignment, CodeFingerprint, JobStatus, MatchedSegment, ReviewStatus, SimilarityResult, Submission,
    SubmissionStatus, SystemSetting, User, utcnow,
)
from .notifications import notify

log = logging.getLogger(__name__)

FILE_SEPARATOR = "\n"


def build_files(sub: Submission, language: str) -> list[tuple[str, str]]:
    """(filename, source) for every file of the assignment language, in stable order."""
    return [(f.filename, f.content) for f in sorted(sub.files, key=lambda f: f.filename)
            if f.language_key == language and f.content.strip()]


def load_engine_config(db: Session, assignment: Assignment, overrides: dict | None = None) -> EngineConfig:
    row = db.get(SystemSetting, "detection")
    cfg = EngineConfig.from_dict(row.value if row else None)
    if assignment.review_threshold is not None:
        cfg.review_threshold = assignment.review_threshold
    if assignment.high_threshold is not None:
        cfg.high_threshold = assignment.high_threshold
    if overrides:
        cfg = EngineConfig.from_dict({**cfg.to_dict(), **{k: v for k, v in overrides.items() if v is not None}})
    return cfg


def store_fingerprints(db: Session, sub: Submission, language: str) -> None:
    """Persist winnowing fingerprints of a submission (used for fast candidate look-ups)."""
    db.query(CodeFingerprint).filter(CodeFingerprint.submission_id == sub.id).delete()
    cfg = DetectionConfig()
    rows: list[CodeFingerprint] = []
    for name, text in build_files(sub, language):
        pf = prepare_file(text, language, name, cfg)
        rows.extend(CodeFingerprint(submission_id=sub.id, hash=h, position=pos) for h, pos in pf.fingerprints)
    db.bulk_save_objects(rows)


def _latest_per_student(subs: list[Submission]) -> list[Submission]:
    latest: dict[tuple[int, int], Submission] = {}
    for s in subs:
        key = (s.assignment_id, s.student_id)
        if key not in latest or s.version > latest[key].version:
            latest[key] = s
    return list(latest.values())


def _history_candidates(db: Session, assignment: Assignment, job: AnalysisJob, requester: User | None) -> list[Submission]:
    stmt = select(Submission).join(Assignment, Assignment.id == Submission.assignment_id).where(
        Submission.assignment_id != assignment.id, Assignment.language_key == assignment.language_key)
    if not job.include_other_assignments:
        # permission boundary: instructors may only reach back into their own assignments
        stmt = stmt.where(Assignment.created_by == assignment.created_by)
    return _latest_per_student(list(db.scalars(stmt).unique()))


def run_job(db: Session, job_id: int) -> None:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        return
    job.status, job.started_at, job.error = JobStatus.running, utcnow(), None
    db.commit()
    try:
        _run(db, job)
    except Exception as exc:  # record and surface failures instead of losing them
        log.exception("analysis job %s failed", job_id)
        db.rollback()
        job = db.get(AnalysisJob, job_id)
        job.status, job.error, job.finished_at = JobStatus.failed, str(exc)[:1000], utcnow()
        for s in db.scalars(select(Submission).where(Submission.assignment_id == job.assignment_id, Submission.status == SubmissionStatus.analyzing)):
            s.status = SubmissionStatus.failed
        db.commit()


def _run(db: Session, job: AnalysisJob) -> None:
    assignment = db.get(Assignment, job.assignment_id)
    language = assignment.language_key
    requester = db.get(User, job.requested_by) if job.requested_by else None
    cfg = load_engine_config(db, assignment, job.config or None)
    engine = DetectionEngine(cfg)

    subs = _latest_per_student(list(db.scalars(select(Submission).where(Submission.assignment_id == assignment.id))))
    main: dict[int, list[tuple[str, str]]] = {}
    for s in subs:
        files = build_files(s, language)
        if files:
            main[s.id] = files
    extra: dict[int, list[tuple[str, str]]] = {}
    if job.include_history or job.include_other_assignments:
        for s in _history_candidates(db, assignment, job, requester):
            files = build_files(s, language)
            if files and s.id not in main:
                extra[s.id] = files

    template = [(r.filename, r.content) for r in assignment.reference_files] or None
    job.total_pairs, job.done_pairs = DetectionEngine.pair_count(len(main), len(extra)), 0
    for s in subs:
        if s.id in main:
            s.status = SubmissionStatus.analyzing
    db.commit()

    # a rerun replaces earlier unreviewed results of this assignment; reviewed ones are preserved
    db.query(SimilarityResult).filter(SimilarityResult.assignment_id == assignment.id, SimilarityResult.review_status == ReviewStatus.pending).delete()
    db.commit()

    best: dict[int, float] = {}
    batch_done = 0

    def progress(done: int, total: int) -> None:
        nonlocal batch_done
        batch_done = done
        if done % 10 == 0 or done == total:
            job.done_pairs = done
            db.commit()

    for id_a, id_b, res in engine.compare_batch(main, language, template, progress, extra):
        row = SimilarityResult(
            job_id=job.id, assignment_id=assignment.id, submission_a_id=id_a, submission_b_id=id_b,
            overall=res.overall, scores=res.scores, confidence=res.confidence, confidence_label=res.confidence_label,
            risk_level=res.risk_level, is_duplicate=res.is_duplicate, explanations=res.explanations,
            ml_probability=res.ml_probability,
        )
        db.add(row)
        db.flush()
        for seg in res.segments:
            db.add(MatchedSegment(result_id=row.id, a_file=seg["a_file"], b_file=seg["b_file"],
                                  a_start_line=seg["a_start_line"], a_end_line=max(seg["a_end_line"], seg["a_start_line"]),
                                  b_start_line=seg["b_start_line"], b_end_line=max(seg["b_end_line"], seg["b_start_line"]),
                                  token_count=seg["token_count"]))
        for sid in (id_a, id_b):
            best[sid] = max(best.get(sid, 0.0), res.overall)
    db.commit()

    for s in subs:
        if s.id in main:
            s.status = SubmissionStatus.analyzed
            s.max_similarity = best.get(s.id, 0.0)
    job.status, job.finished_at, job.done_pairs = JobStatus.completed, utcnow(), job.total_pairs
    db.commit()

    flagged = db.query(SimilarityResult).filter(SimilarityResult.job_id == job.id, SimilarityResult.overall >= cfg.review_threshold).count()
    if requester:
        notify(db, requester, f"Analysis complete: {assignment.title}",
               f"{job.total_pairs} comparison(s) finished; {flagged} pair(s) at or above the review threshold.",
               f"/assignments/{assignment.id}/analysis")
