import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..core.config import get_settings
from ..core.deps import get_current_user
from ..database import get_db
from ..models import Assignment, Submission, SubmissionFile, SubmissionStatus, User, utcnow
from ..schemas import FileContentOut, SubmissionOut
from ..services.analysis_service import store_fingerprints
from ..services.audit import audit
from ..services.files import UploadError, collect_files, store_bytes
from ..services.notifications import notify
from .common import aware, submission_out

router = APIRouter(tags=["submissions"])


def _can_view(db: Session, sub: Submission, user: User) -> None:
    if user.role_name == "admin":
        return
    if user.role_name == "student":
        if sub.student_id == user.id:
            return
        # group assignment: members of the same group may view each other's submission
        if sub.group_id and any(m.id == user.id for m in sub.group.members):
            return
        raise HTTPException(403, "You can only view your own submissions")
    if sub.assignment.created_by != user.id:
        raise HTTPException(403, "This submission belongs to another instructor's assignment")


def _load(db: Session, submission_id: int) -> Submission:
    sub = db.scalar(select(Submission).where(Submission.id == submission_id).options(selectinload(Submission.files)))
    if not sub:
        raise HTTPException(404, "Submission not found")
    return sub


@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionOut, status_code=201)
async def upload_submission(
    assignment_id: int, request: Request, files: list[UploadFile] = File(...),
    student_id: int | None = Form(default=None), group_id: int | None = Form(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Students upload their own work; faculty (assignment owner) and admins may upload on a student's behalf."""
    assignment = db.get(Assignment, assignment_id)
    if not assignment or (user.role_name == "student" and not assignment.is_published):
        raise HTTPException(404, "Assignment not found")
    if user.role_name == "student":
        target = user
    else:
        if user.role_name == "faculty" and assignment.created_by != user.id:
            raise HTTPException(403, "This assignment belongs to another instructor")
        if student_id is None:
            raise HTTPException(400, "student_id is required when uploading on behalf of a student")
        target = db.get(User, student_id)
        if not target or target.role_name != "student":
            raise HTTPException(400, "student_id must refer to a student")

    group = None
    if assignment.is_group:
        group = next((g for g in assignment.groups if (group_id is None or g.id == group_id) and any(m.id == target.id for m in g.members)), None)
        if group is None:
            raise HTTPException(400, "This is a group assignment: the student must belong to a group of this assignment")

    s = get_settings()
    raw: list[tuple[str, bytes]] = []
    for f in files:
        name = f.filename or ""
        limit = s.max_zip_bytes if name.lower().endswith(".zip") else s.max_upload_bytes
        data = await f.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"{name[:60]} is too large")
        raw.append((name, data))
    try:
        incoming = collect_files(raw, {assignment.language_key})
    except UploadError as exc:
        audit(db, user.id, "submission.rejected", request, "assignment", assignment.id, reason=str(exc)[:200])
        raise HTTPException(400, str(exc))

    content_hash = hashlib.sha256("".join(sorted(hashlib.sha256(f.data).hexdigest() for f in incoming)).encode()).hexdigest()
    version = (db.scalar(select(func.max(Submission.version)).where(Submission.assignment_id == assignment.id, Submission.student_id == target.id)) or 0) + 1
    duplicate = db.scalar(select(Submission).where(Submission.assignment_id == assignment.id, Submission.content_hash == content_hash,
                                                   Submission.student_id != target.id).order_by(Submission.id))
    deadline = aware(assignment.deadline)
    sub = Submission(assignment_id=assignment.id, student_id=target.id, group_id=group.id if group else None, uploaded_by=user.id,
                     version=version, status=SubmissionStatus.uploaded, content_hash=content_hash,
                     is_late=bool(deadline and utcnow() > deadline), duplicate_of_id=duplicate.id if duplicate else None)
    db.add(sub)
    db.flush()
    for f in incoming:
        db.add(SubmissionFile(submission_id=sub.id, filename=f.filename, stored_name=store_bytes(f.data, "submissions"),
                              size_bytes=len(f.data), sha256=hashlib.sha256(f.data).hexdigest(), language_key=f.language_key, content=f.text))
    db.commit()
    sub = _load(db, sub.id)
    store_fingerprints(db, sub, assignment.language_key)
    db.commit()
    audit(db, user.id, "submission.create", request, "submission", sub.id, assignment_id=assignment.id, files=len(incoming), version=version)
    if duplicate:
        owner = db.get(User, assignment.created_by)
        notify(db, owner, "Duplicate submission detected",
               f"A submission for '{assignment.title}' is byte-identical to another student's work.", f"/assignments/{assignment.id}/analysis")
    return submission_out(sub)


@router.get("/submissions/mine")
def my_submissions(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Submission).where(Submission.student_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Submission.submitted_at.desc()).limit(page_size).offset((page - 1) * page_size)
                      .options(selectinload(Submission.files))).all()
    return {"items": [submission_out(r) for r in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/assignments/{assignment_id}/submissions")
def list_submissions(assignment_id: int, q: str = "", status: str | None = None, sort: str = "-submitted_at", latest_only: bool = False,
                     page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(404, "Assignment not found")
    stmt = select(Submission).join(User, User.id == Submission.student_id).where(Submission.assignment_id == a.id)
    if user.role_name == "student":
        stmt = stmt.where(Submission.student_id == user.id)
    elif user.role_name == "faculty" and a.created_by != user.id:
        raise HTTPException(403, "This assignment belongs to another instructor")
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(User.full_name).like(like), func.lower(User.email).like(like)))
    if status:
        try:
            stmt = stmt.where(Submission.status == SubmissionStatus(status))
        except ValueError:
            raise HTTPException(400, "Unknown status")
    if latest_only:
        newest = select(func.max(Submission.id)).where(Submission.assignment_id == a.id).group_by(Submission.student_id)
        stmt = stmt.where(Submission.id.in_(newest))  # versions grow with id, so max(id) is the latest upload
    cols = {"submitted_at": Submission.submitted_at, "student": User.full_name, "similarity": Submission.max_similarity, "status": Submission.status}
    col = cols.get(sort.lstrip("-"), Submission.submitted_at)
    stmt = stmt.order_by(col.desc() if sort.startswith("-") else col.asc())
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size).options(selectinload(Submission.files))).unique().all()
    out = [submission_out(r) for r in rows]
    if user.role_name == "student":
        for o in out:
            o.max_similarity = None  # students receive similarity only through the feedback endpoint
    return {"items": out, "total": total, "page": page, "page_size": page_size}


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _load(db, submission_id)
    _can_view(db, sub, user)
    out = submission_out(sub)
    if user.role_name == "student":
        out.max_similarity = None
    return out


@router.get("/submissions/{submission_id}/files/{file_id}", response_model=FileContentOut)
def get_file(submission_id: int, file_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Source is only served through this authorised endpoint; the storage directory is never exposed."""
    sub = _load(db, submission_id)
    _can_view(db, sub, user)
    f = next((x for x in sub.files if x.id == file_id), None)
    if not f:
        raise HTTPException(404, "File not found")
    return FileContentOut(id=f.id, filename=f.filename, language_key=f.language_key, content=f.content)


@router.delete("/submissions/{submission_id}", status_code=204)
def delete_submission(submission_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = _load(db, submission_id)
    if user.role_name == "student":
        raise HTTPException(403, "Students cannot delete submissions; upload a new version instead")
    _can_view(db, sub, user)
    db.delete(sub)
    db.commit()
    audit(db, user.id, "submission.delete", request, "submission", submission_id)
