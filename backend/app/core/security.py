import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

_PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


def validate_password_strength(password: str) -> None:
    if not _PASSWORD_RULE.match(password):
        raise ValueError("Password must be 8-128 characters and contain at least one letter and one digit")


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes; hash a digest to avoid silent truncation
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")
    return bcrypt.hashpw(digest, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")
    try:
        return bcrypt.checkpw(digest, hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=s.access_token_expire_minutes)}
    return jwt.encode(payload, s.secret_key, algorithm=s.algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.secret_key, algorithms=[s.algorithm], options={"require": ["exp", "sub"]})


def new_reset_token() -> tuple[str, str]:
    """Returns (token to e-mail, sha256 hash to store)."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
