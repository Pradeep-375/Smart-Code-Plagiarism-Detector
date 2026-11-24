from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.deps import get_assignment_for_staff, get_current_user, require_staff
from ..database import get_db
from ..models import Assignment, AssignmentGroup, ProgrammingLanguage, ReferenceFile, Submission, User
from ..schemas import AssignmentIn, AssignmentOut, AssignmentUpdateIn, GroupIn, GroupOut, UserOut
from ..services.audit import audit
from ..services.files import UploadError, collect_files

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _out(db: Session, a: Assignment, user: User) -> AssignmentOut:
    count = db.scalar(select(func.count()).select_from(Submission).where(Submission.assignment_id == a.id)) or 0
    out = AssignmentOut.model_validate(a)
    if user.role_name == "student":
        mine = db.scalar(select(func.count()).select_from(Submission).where(Submission.assignment_id == a.id, Submission.student_id == user.id))
        out.my_submission_count = mine or 0
        out.submission_count = 0  # students never see class-wide numbers
    else:
        out.submission_count = count
    return out


def _check_language(db: Session, key: str) -> None:
    if not db.scalar(select(ProgrammingLanguage).where(ProgrammingLanguage.key == key, ProgrammingLanguage.enabled.is_(True))):
        raise HTTPException(400, f"Language '{key}' is not enabled")


def _check_thresholds(review: float | None, high: float | None) -> None:
    if review is not None and high is not None and high < review:
        raise HTTPException(400, "High threshold must not be lower than the review threshold")


@router.get("")
def list_assignments(q: str = "", language: str | None = None, sort: str = "-created_at", page: int = Query(1, ge=1),
                     page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Assignment)
    if user.role_name == "faculty":
        stmt = stmt.where(Assignment.created_by == user.id)
    elif user.role_name == "student":
        stmt = stmt.where(Assignment.is_published.is_(True))
    if q:
        stmt = stmt.where(func.lower(Assignment.title).like(f"%{q.lower()}%"))
    if language:
        stmt = stmt.where(Assignment.language_key == language)
    columns = {"created_at": Assignment.created_at, "title": Assignment.title, "deadline": Assignment.deadline}
    col = columns.get(sort.lstrip("-"), Assignment.created_at)
    stmt = stmt.order_by(col.desc() if sort.startswith("-") else col.asc())
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).all()
    return {"items": [_out(db, a, user) for a in rows], "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=AssignmentOut, status_code=201)
def create_assignment(body: AssignmentIn, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    _check_language(db, body.language_key)
    _check_thresholds(body.review_threshold, body.high_threshold)
    a = Assignment(**body.model_dump(), created_by=user.id)
    db.add(a)
    db.commit()
    db.refresh(a)
    audit(db, user.id, "assignment.create", request, "assignment", a.id, title=a.title)
    return _out(db, a, user)


@router.get("/{assignment_id}", response_model=AssignmentOut)
def get_assignment(assignment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Assignment, assignment_id)
    if not a or (user.role_name == "student" and not a.is_published):
        raise HTTPException(404, "Assignment not found")
    if user.role_name == "faculty" and a.created_by != user.id:
        raise HTTPException(403, "This assignment belongs to another instructor")
    return _out(db, a, user)


@router.patch("/{assignment_id}", response_model=AssignmentOut)
def update_assignment(assignment_id: int, body: AssignmentUpdateIn, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    data = body.model_dump(exclude_unset=True)
    if "language_key" in data:
        _check_language(db, data["language_key"])
        if data["language_key"] != a.language_key and db.scalar(select(func.count()).select_from(Submission).where(Submission.assignment_id == a.id)):
            raise HTTPException(409, "The language cannot be changed after submissions exist")
    _check_thresholds(data.get("review_threshold", a.review_threshold), data.get("high_threshold", a.high_threshold))
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    audit(db, user.id, "assignment.update", request, "assignment", a.id, changes=sorted(data))
    return _out(db, a, user)


@router.delete("/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    title = a.title
    db.delete(a)
    db.commit()
    audit(db, user.id, "assignment.delete", request, "assignment", assignment_id, title=title)


# ---- groups -----------------------------------------------------------------------------
def _group_out(g: AssignmentGroup) -> GroupOut:
    return GroupOut(id=g.id, name=g.name, members=[UserOut.model_validate(m) for m in g.members])


def _members(db: Session, ids: list[int]) -> list[User]:
    users = db.scalars(select(User).where(User.id.in_(ids))).unique().all() if ids else []
    if len(users) != len(set(ids)) or any(u.role_name != "student" for u in users):
        raise HTTPException(400, "All group members must be existing students")
    return list(users)


@router.get("/{assignment_id}/groups", response_model=list[GroupOut])
def list_groups(assignment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(404, "Assignment not found")
    groups = list(a.groups)
    if user.role_name == "student":
        groups = [g for g in groups if any(m.id == user.id for m in g.members)]
    elif user.role_name == "faculty" and a.created_by != user.id:
        raise HTTPException(403, "This assignment belongs to another instructor")
    return [_group_out(g) for g in groups]


@router.post("/{assignment_id}/groups", response_model=GroupOut, status_code=201)
def create_group(assignment_id: int, body: GroupIn, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    if not a.is_group:
        raise HTTPException(400, "This is an individual assignment")
    if db.scalar(select(AssignmentGroup).where(AssignmentGroup.assignment_id == a.id, AssignmentGroup.name == body.name)):
        raise HTTPException(409, "A group with this name already exists")
    members = _members(db, body.member_ids)
    taken = {m.id for g in a.groups for m in g.members}
    if any(m.id in taken for m in members):
        raise HTTPException(409, "A student can belong to only one group per assignment")
    g = AssignmentGroup(assignment_id=a.id, name=body.name.strip(), members=members)
    db.add(g)
    db.commit()
    db.refresh(g)
    audit(db, user.id, "group.create", request, "group", g.id, assignment_id=a.id)
    return _group_out(g)


@router.put("/{assignment_id}/groups/{group_id}", response_model=GroupOut)
def update_group(assignment_id: int, group_id: int, body: GroupIn, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    g = db.get(AssignmentGroup, group_id)
    if not g or g.assignment_id != a.id:
        raise HTTPException(404, "Group not found")
    members = _members(db, body.member_ids)
    taken = {m.id for other in a.groups if other.id != g.id for m in other.members}
    if any(m.id in taken for m in members):
        raise HTTPException(409, "A student can belong to only one group per assignment")
    g.name, g.members = body.name.strip(), members
    db.commit()
    audit(db, user.id, "group.update", request, "group", g.id)
    return _group_out(g)


@router.delete("/{assignment_id}/groups/{group_id}", status_code=204)
def delete_group(assignment_id: int, group_id: int, request: Request, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    g = db.get(AssignmentGroup, group_id)
    if not g or g.assignment_id != a.id:
        raise HTTPException(404, "Group not found")
    db.delete(g)
    db.commit()
    audit(db, user.id, "group.delete", request, "group", group_id)


# ---- reference (starter) files ---------------------------------------------------------------
@router.get("/{assignment_id}/reference-files")
def list_reference_files(assignment_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    return [{"id": r.id, "filename": r.filename, "size": len(r.content), "created_at": r.created_at} for r in a.reference_files]


@router.post("/{assignment_id}/reference-files", status_code=201)
async def upload_reference_files(assignment_id: int, request: Request, files: list[UploadFile] = File(...),
                                 user: User = Depends(require_staff), db: Session = Depends(get_db)):
    """Starter/template code. Matches against it are ignored by the winnowing layer (not counted as copying)."""
    a = get_assignment_for_staff(db, assignment_id, user)
    s = get_settings()
    raw = [(f.filename or "file", await f.read(s.max_zip_bytes + 1)) for f in files]
    try:
        incoming = collect_files(raw, {a.language_key})
    except UploadError as exc:
        raise HTTPException(400, str(exc))
    for f in incoming:
        db.add(ReferenceFile(assignment_id=a.id, filename=f.filename, content=f.text))
    db.commit()
    audit(db, user.id, "assignment.reference_upload", request, "assignment", a.id, count=len(incoming))
    return {"uploaded": [f.filename for f in incoming]}


@router.delete("/{assignment_id}/reference-files/{file_id}", status_code=204)
def delete_reference_file(assignment_id: int, file_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)):
    a = get_assignment_for_staff(db, assignment_id, user)
    ref = db.get(ReferenceFile, file_id)
    if not ref or ref.assignment_id != a.id:
        raise HTTPException(404, "File not found")
    db.delete(ref)
    db.commit()
