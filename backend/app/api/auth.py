import hmac
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.deps import get_current_user
from ..core.security import (
    create_access_token, hash_password, hash_token, new_reset_token, verify_password,
)
from ..database import get_db
from ..models import PasswordResetToken, Role, User, utcnow
from ..schemas import (
    ChangePasswordIn, ForgotPasswordIn, LoginIn, ProfileUpdateIn, RegisterIn, ResetPasswordIn, TokenOut, UserOut,
)
from ..services.audit import audit
from ..services.notifications import send_email
from .common import aware

router = APIRouter(prefix="/auth", tags=["auth"])

# A valid bcrypt hash used to keep login timing similar for unknown e-mail addresses.
_DUMMY_HASH = hash_password("dummy-password-1")


def _token_response(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id, user.role_name), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    """Self-registration for students and (with an access code) faculty. Admin accounts can never be self-registered:
    the schema rejects ``role="admin"`` and administrators are created by the seed process or by another admin."""
    s = get_settings()
    if body.role == "faculty":
        expected = s.faculty_registration_code
        if not expected:
            raise HTTPException(403, "Faculty self-registration is not enabled. Ask an administrator to create your account.")
        # constant-time comparison; the auth rate limiter also applies to this endpoint
        if not body.faculty_code or not hmac.compare_digest(body.faculty_code.encode("utf-8"), expected.encode("utf-8")):
            audit(db, None, "auth.register_denied", request, reason="bad_faculty_code")
            raise HTTPException(403, "Invalid faculty access code")

    email = body.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(409, "An account with this e-mail already exists")
    role = db.scalar(select(Role).where(Role.name == body.role))
    if role is None:  # roles are created at startup (seed_base); never fall back to another role silently
        raise HTTPException(500, f"Role '{body.role}' is not configured")
    user = User(email=email, full_name=body.full_name.strip(), hashed_password=hash_password(body.password),
                role_id=role.id, organization_id=body.organization_id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two simultaneous registrations with the same e-mail
        db.rollback()
        raise HTTPException(409, "An account with this e-mail already exists")
    db.refresh(user)
    audit(db, user.id, "auth.register", request, "user", user.id, role=role.name)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    ok = verify_password(body.password, user.hashed_password if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        audit(db, user.id if user else None, "auth.login_failed", request, "user", user.id if user else None)
        raise HTTPException(401, "Incorrect e-mail or password")
    user.last_login_at = utcnow()
    db.commit()
    audit(db, user.id, "auth.login", request, "user", user.id)
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileUpdateIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    audit(db, user.id, "profile.update", request, "user", user.id)
    return user


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    audit(db, user.id, "auth.password_changed", request, "user", user.id)


@router.post("/forgot-password", status_code=202)
def forgot_password(body: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    """Always answers 202 so the endpoint cannot be used to discover registered e-mail addresses."""
    s = get_settings()
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower(), User.is_active.is_(True)))
    if user:
        token, token_hash = new_reset_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=utcnow() + timedelta(minutes=s.password_reset_minutes)))
        db.commit()
        link = f"{s.frontend_url}/reset-password?token={token}"
        send_email(user.email, "Reset your password", f"Use this link within {s.password_reset_minutes} minutes:\n{link}\n\nIf you did not request this, ignore this e-mail.")
        audit(db, user.id, "auth.password_reset_requested", request, "user", user.id)
    return {"detail": "If that address is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=204)
def reset_password(body: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(body.token)))
    if not row or row.used or aware(row.expires_at) < utcnow():
        raise HTTPException(400, "Reset link is invalid or has expired")
    user = db.get(User, row.user_id)
    user.hashed_password = hash_password(body.new_password)
    row.used = True
    db.commit()
    audit(db, user.id, "auth.password_reset", request, "user", user.id)
