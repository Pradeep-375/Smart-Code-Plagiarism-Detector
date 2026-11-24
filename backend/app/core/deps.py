from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Assignment, User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role_name not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user
    return checker


require_admin = require_roles("admin")
require_staff = require_roles("admin", "faculty")


def get_assignment_for_staff(db: Session, assignment_id: int, user: User) -> Assignment:
    """Faculty may only touch their own assignments; admins may touch all."""
    a = db.get(Assignment, assignment_id)
    if a is None:
        raise HTTPException(404, "Assignment not found")
    if user.role_name != "admin" and a.created_by != user.id:
        raise HTTPException(403, "This assignment belongs to another instructor")
    return a
