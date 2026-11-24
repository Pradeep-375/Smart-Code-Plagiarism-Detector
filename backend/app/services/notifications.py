import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models import Notification, User

log = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send via SMTP when configured, otherwise log (development)."""
    s = get_settings()
    if not s.smtp_host:
        log.info("[email disabled] to=%s subject=%s", to, subject)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.smtp_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:  # never break the request because mail failed
        log.exception("failed to send email to %s", to)
        return False


def notify(db: Session, user: User, title: str, message: str = "", link: str | None = None, email: bool = True) -> None:
    db.add(Notification(user_id=user.id, title=title, message=message, link=link))
    db.commit()
    if email and user.email_notifications:
        send_email(user.email, title, f"{message}\n\n{get_settings().frontend_url}{link or ''}")
