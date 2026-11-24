from fastapi import Request
from sqlalchemy.orm import Session

from ..models import AuditLog


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def audit(db: Session, user_id: int | None, action: str, request: Request | None = None,
          entity_type: str | None = None, entity_id: int | None = None, **details) -> None:
    """Append an audit entry. Never include secrets in ``details``."""
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id,
                    ip_address=client_ip(request), details=details))
    db.commit()
