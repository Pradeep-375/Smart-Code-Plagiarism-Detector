from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user, require_admin
from ..database import get_db
from ..detection_engine import ALGORITHMS, DEFAULT_WEIGHTS
from ..models import AuditLog, ProgrammingLanguage, SystemSetting, User
from ..schemas import AuditLogOut, DetectionSettingsIn, LanguageIn, LanguageOut
from ..services.audit import audit
from .common import DEFAULT_DETECTION, detection_settings

router = APIRouter(tags=["admin"])


@router.get("/languages", response_model=list[LanguageOut])
def list_languages(all: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(ProgrammingLanguage).order_by(ProgrammingLanguage.name)
    if not (all and user.role_name == "admin"):
        stmt = stmt.where(ProgrammingLanguage.enabled.is_(True))
    return db.scalars(stmt).all()


@router.post("/admin/languages", response_model=LanguageOut, status_code=201)
def create_language(body: LanguageIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from ..detection_engine import SUPPORTED_LANGUAGES
    if body.key not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"The detection engine supports only: {', '.join(SUPPORTED_LANGUAGES)}")
    if db.scalar(select(ProgrammingLanguage).where(ProgrammingLanguage.key == body.key)):
        raise HTTPException(409, "Language already exists")
    lang = ProgrammingLanguage(**body.model_dump())
    db.add(lang)
    db.commit()
    db.refresh(lang)
    audit(db, admin.id, "language.create", request, "language", lang.id, key=lang.key)
    return lang


@router.patch("/admin/languages/{language_id}", response_model=LanguageOut)
def update_language(language_id: int, body: LanguageIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    lang = db.get(ProgrammingLanguage, language_id)
    if not lang:
        raise HTTPException(404, "Language not found")
    lang.name, lang.extensions, lang.enabled = body.name, body.extensions, body.enabled
    db.commit()
    audit(db, admin.id, "language.update", request, "language", lang.id, enabled=lang.enabled)
    return lang


@router.get("/admin/settings/detection")
def get_detection_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {**detection_settings(db).to_dict(), "algorithms": list(ALGORITHMS), "defaults": DEFAULT_DETECTION}


@router.put("/admin/settings/detection")
def put_detection_settings(body: DetectionSettingsIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    current = detection_settings(db).to_dict()
    if body.weights is not None:
        unknown = set(body.weights) - set(ALGORITHMS)
        if unknown:
            raise HTTPException(400, f"Unknown algorithms: {', '.join(sorted(unknown))}")
        if any(v < 0 for v in body.weights.values()) or sum(body.weights.values()) <= 0:
            raise HTTPException(400, "Weights must be non-negative and sum to more than zero")
        current["weights"] = {**DEFAULT_WEIGHTS, **body.weights}
    if body.review_threshold is not None:
        current["review_threshold"] = body.review_threshold
    if body.high_threshold is not None:
        current["high_threshold"] = body.high_threshold
    if current["high_threshold"] < current["review_threshold"]:
        raise HTTPException(400, "High threshold must not be lower than the review threshold")
    row = db.get(SystemSetting, "detection")
    if row:
        row.value = current
    else:
        db.add(SystemSetting(key="detection", value=current))
    db.commit()
    audit(db, admin.id, "settings.detection_update", request, "setting")
    return {**detection_settings(db).to_dict(), "algorithms": list(ALGORITHMS)}


@router.get("/admin/audit-logs")
def audit_logs(action: str | None = None, user_id: int | None = None, q: str = "", since: datetime | None = None,
               until: datetime | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
               admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if since:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until:
        stmt = stmt.where(AuditLog.created_at <= until)
    if q:
        stmt = stmt.where(AuditLog.action.like(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.id.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    items = [AuditLogOut(id=r.id, user_id=r.user_id, user_email=r.user.email if r.user else None, action=r.action,
                         entity_type=r.entity_type, entity_id=r.entity_id, ip_address=r.ip_address, details=r.details or {},
                         created_at=r.created_at) for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
