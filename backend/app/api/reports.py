import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_assignment_for_staff, require_staff
from ..database import get_db
from ..models import Report, SimilarityResult, Submission, User, utcnow
from ..reports.pdf import build_assignment_report, build_pair_report
from ..services.audit import audit
from ..services.files import resolve_stored, store_bytes
from .analysis import _result_query, _staff_result
from .common import aware, party_label, review_threshold_for

router = APIRouter(tags=["reports"])


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection (=, +, -, @ at the start of a cell)."""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@router.get("/results/{result_id}/report.pdf")
def pair_report(result_id: int, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    r = _staff_result(db, result_id, user)
    a_sub, b_sub = r.submission_a, r.submission_b
    assignment = a_sub.assignment
    lang = assignment.language_key
    reviewer = db.get(User, r.reviewed_by) if r.reviewed_by else None
    data = {
        "assignment": {"title": assignment.title, "language_key": lang, "deadline": assignment.deadline, "description": assignment.description},
        "generated_at": utcnow(), "generated_by": user.full_name, "analyzed_at": r.created_at,
        "student_a": party_label(a_sub, assignment.id), "student_b": party_label(b_sub, assignment.id),
        "submission_a": {"id": a_sub.id, "submitted_at": a_sub.submitted_at, "files": [f.filename for f in a_sub.files]},
        "submission_b": {"id": b_sub.id, "submitted_at": b_sub.submitted_at, "files": [f.filename for f in b_sub.files]},
        "result": {
            "overall": r.overall, "scores": r.scores, "confidence": r.confidence, "confidence_label": r.confidence_label,
            "risk_level": r.risk_level, "is_duplicate": r.is_duplicate, "explanations": r.explanations,
            "review_status": r.review_status.value, "review_notes": r.review_notes, "override_score": r.override_score,
            "reviewer": reviewer.full_name if reviewer else None, "reviewed_at": r.reviewed_at,
            "segments": [{"a_file": s.a_file, "b_file": s.b_file, "a_start_line": s.a_start_line, "a_end_line": s.a_end_line,
                          "b_start_line": s.b_start_line, "b_end_line": s.b_end_line, "token_count": s.token_count} for s in r.segments],
        },
        "files_a": {f.filename: f.content for f in a_sub.files if f.language_key == lang},
        "files_b": {f.filename: f.content for f in b_sub.files if f.language_key == lang},
    }
    pdf = build_pair_report(data)
    db.add(Report(kind="pair", assignment_id=r.assignment_id, result_id=r.id, generated_by=user.id, stored_name=store_bytes(pdf, "reports")))
    db.commit()
    audit(db, user.id, "report.pair", request, "result", r.id)
    return _pdf_response(pdf, f"similarity-report-{r.id}.pdf")


def _assignment_rows(db: Session, assignment_id: int):
    rows = db.scalars(_result_query([assignment_id]).order_by(SimilarityResult.overall.desc())).unique().all()
    return rows


@router.get("/assignments/{assignment_id}/report.pdf")
def assignment_report(assignment_id: int, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    rows = _assignment_rows(db, a.id)
    threshold = review_threshold_for(db, a)
    subs = db.scalars(select(Submission).where(Submission.assignment_id == a.id)).all()
    data = {
        "assignment": {"title": a.title, "language_key": a.language_key, "deadline": a.deadline},
        "generated_at": utcnow(), "generated_by": user.full_name,
        "stats": {"submissions": len(subs), "analyzed": sum(1 for s in subs if s.status.value == "analyzed"), "pairs": len(rows),
                  "average": (sum(r.effective_score for r in rows) / len(rows)) if rows else 0.0,
                  "flagged": sum(1 for r in rows if r.effective_score >= threshold), "review_threshold": threshold},
        "rows": [{"student_a": party_label(r.submission_a, a.id), "student_b": party_label(r.submission_b, a.id), "overall": r.effective_score,
                  "risk_level": r.risk_level, "confidence_label": r.confidence_label, "review_status": r.review_status.value} for r in rows],
    }
    pdf = build_assignment_report(data)
    db.add(Report(kind="assignment", assignment_id=a.id, generated_by=user.id, stored_name=store_bytes(pdf, "reports")))
    db.commit()
    audit(db, user.id, "report.assignment", request, "assignment", a.id)
    return _pdf_response(pdf, f"assignment-{a.id}-report.pdf")


@router.get("/assignments/{assignment_id}/export.csv")
def export_csv(assignment_id: int, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["result_id", "student_a", "student_b", "overall_percent", "effective_percent", "risk", "confidence", "duplicate", "review_status"])
    for r in _assignment_rows(db, a.id):
        w.writerow([r.id, _csv_safe(party_label(r.submission_a, a.id)), _csv_safe(party_label(r.submission_b, a.id)),
                    round(r.overall * 100, 1), round(r.effective_score * 100, 1), r.risk_level, r.confidence_label, r.is_duplicate, r.review_status.value])
    audit(db, user.id, "report.csv", request, "assignment", a.id)
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="assignment-{a.id}.csv"'})


@router.get("/reports/{report_id}/download")
def download_saved_report(report_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    rep = db.get(Report, report_id)
    if not rep:
        raise HTTPException(404, "Report not found")
    get_assignment_for_staff(db, rep.assignment_id, user)
    return _pdf_response(resolve_stored("reports", rep.stored_name).read_bytes(), f"report-{rep.id}.pdf")


@router.get("/assignments/{assignment_id}/reports")
def list_reports(assignment_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    get_assignment_for_staff(db, assignment_id, user)
    rows = db.scalars(select(Report).where(Report.assignment_id == assignment_id).order_by(Report.id.desc()).limit(50)).all()
    return [{"id": r.id, "kind": r.kind, "result_id": r.result_id, "created_at": r.created_at} for r in rows]
