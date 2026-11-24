from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..core.deps import require_admin, require_staff
from ..core.security import hash_password
from ..database import get_db
from ..models import Role, User
from ..schemas import UserCreateIn, UserOut, UserUpdateIn
from ..services.audit import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(q: str = "", role: str | None = None, active: bool | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(20, ge=1, le=100), admin: User = Depends(require_staff), db: Session = Depends(get_db)):
    stmt = select(User).join(Role)
    if admin.role_name != "admin":
        stmt = stmt.where(Role.name == "student")  # faculty may look up students (e.g. to build groups) only
    elif role:
        stmt = stmt.where(Role.name == role)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like)))
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(User.created_at.desc()).limit(page_size).offset((page - 1) * page_size)).unique().all()
    return {"items": [UserOut.model_validate(u) for u in rows], "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreateIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(409, "An account with this e-mail already exists")
    role = db.scalar(select(Role).where(Role.name == body.role))
    user = User(email=body.email.lower(), full_name=body.full_name.strip(), hashed_password=hash_password(body.password),
                role_id=role.id, organization_id=body.organization_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, admin.id, "user.create", request, "user", user.id, role=body.role)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdateIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    data = body.model_dump(exclude_unset=True)
    if user.id == admin.id and (data.get("is_active") is False or (data.get("role") and data["role"] != "admin")):
        raise HTTPException(400, "You cannot deactivate or demote your own account")
    if "role" in data and data["role"]:
        user.role_id = db.scalar(select(Role.id).where(Role.name == data.pop("role")))
    data.pop("role", None)
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    audit(db, admin.id, "user.update", request, "user", user.id, changes=sorted(body.model_dump(exclude_unset=True)))
    return user


@router.delete("/{user_id}", status_code=204)
def deactivate_user(user_id: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Soft delete: accounts own submissions and audit history, so they are deactivated rather than removed."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot deactivate your own account")
    user.is_active = False
    db.commit()
    audit(db, admin.id, "user.deactivate", request, "user", user.id)
