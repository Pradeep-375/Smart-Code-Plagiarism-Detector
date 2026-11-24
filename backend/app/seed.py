"""Bootstrap data: roles, languages, default detection settings, first admin and optional demo data."""
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.config import get_settings
from .core.security import hash_password
from .detection_engine.samples import PY, PY_RESTRUCTURED, change_comments_python, rename_python, reorder_python
from .models import (
    AnalysisJob, Assignment, ProgrammingLanguage, Role, Submission, SubmissionFile, SubmissionStatus, SystemSetting, User, utcnow,
)
from .api.common import DEFAULT_DETECTION
from .services.analysis_service import run_job, store_fingerprints

log = logging.getLogger(__name__)

ROLES = {"admin": "Manages users, languages, settings and audit logs", "faculty": "Creates assignments and reviews similarity",
         "student": "Submits code and views permitted feedback"}
LANGUAGES = [("python", "Python", ".py"), ("java", "Java", ".java"), ("c", "C", ".c,.h"), ("cpp", "C++", ".cpp,.cc,.hpp"),
             ("javascript", "JavaScript", ".js"), ("typescript", "TypeScript", ".ts")]


def seed_base(db: Session) -> None:
    for name, desc in ROLES.items():
        if not db.scalar(select(Role).where(Role.name == name)):
            db.add(Role(name=name, description=desc))
    for key, name, ext in LANGUAGES:
        if not db.scalar(select(ProgrammingLanguage).where(ProgrammingLanguage.key == key)):
            db.add(ProgrammingLanguage(key=key, name=name, extensions=ext))
    if not db.get(SystemSetting, "detection"):
        db.add(SystemSetting(key="detection", value=DEFAULT_DETECTION))
    db.commit()

    s = get_settings()
    has_admin = db.scalar(select(User).join(Role).where(Role.name == "admin"))
    if not has_admin:
        if s.seed_admin_password:
            role = db.scalar(select(Role).where(Role.name == "admin"))
            db.add(User(email=s.seed_admin_email.lower(), full_name="System Administrator", hashed_password=hash_password(s.seed_admin_password), role_id=role.id))
            db.commit()
            log.info("Created initial administrator %s", s.seed_admin_email)
        else:
            log.warning("No administrator exists. Set SEED_ADMIN_PASSWORD (and SEED_ADMIN_EMAIL) and restart to create one.")


def _user(db: Session, email: str, name: str, role: str, password: str) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing
    r = db.scalar(select(Role).where(Role.name == role))
    u = User(email=email, full_name=name, hashed_password=hash_password(password), role_id=r.id)
    db.add(u)
    db.commit()
    return u


def _submit(db: Session, assignment: Assignment, student: User, code: str, filename: str = "main.py") -> Submission:
    import hashlib
    h = hashlib.sha256(code.encode()).hexdigest()
    sub = Submission(assignment_id=assignment.id, student_id=student.id, uploaded_by=student.id, status=SubmissionStatus.uploaded,
                     content_hash=hashlib.sha256(h.encode()).hexdigest(), submitted_at=utcnow() - timedelta(hours=len(code) % 48))
    db.add(sub)
    db.flush()
    db.add(SubmissionFile(submission_id=sub.id, filename=filename, stored_name="0" * 32, size_bytes=len(code.encode()), sha256=h, language_key="python", content=code))
    db.commit()
    db.refresh(sub)
    store_fingerprints(db, sub, "python")
    db.commit()
    return sub


def seed_demo(db: Session) -> None:
    """Demonstration data only (SEED_DEMO_DATA=true). All demo accounts use SEED_ADMIN_PASSWORD."""
    s = get_settings()
    if not s.seed_admin_password:
        log.warning("SEED_DEMO_DATA needs SEED_ADMIN_PASSWORD; skipping demo data")
        return
    if db.scalar(select(Assignment).where(Assignment.title == "Demo: Account & Number Utilities")):
        return
    pw = s.seed_admin_password
    faculty = _user(db, "faculty@example.com", "Dr. Meera Rao", "faculty", pw)
    students = [_user(db, f"student{i}@example.com", n, "student", pw) for i, n in
                enumerate(["Asha Verma", "Ben Carter", "Chen Wei", "Divya Nair", "Evan Brooks", "Farah Khan"], start=1)]
    a = Assignment(title="Demo: Account & Number Utilities", description="Implement the account class, prime utilities and word statistics.",
                   language_key="python", created_by=faculty.id, deadline=utcnow() + timedelta(days=7), show_results_to_students=True)
    db.add(a)
    db.commit()
    codes = [
        PY["bank_account"],                                        # Asha (original)
        rename_python(PY["bank_account"]),                         # Ben   - renamed copy of Asha
        PY["prime_tools"],                                      # Chen  (original)
        reorder_python(change_comments_python(PY["prime_tools"])),  # Divya - reordered copy of Chen
        PY["word_stats"],                                    # Evan  (original)
        PY_RESTRUCTURED["prime_tools"],                               # Farah - restructured primes
    ]
    for student, code in zip(students, codes):
        _submit(db, a, student, code)
    job = AnalysisJob(assignment_id=a.id, requested_by=faculty.id, config={}, total_pairs=15)
    db.add(job)
    db.commit()
    run_job(db, job.id)
    log.info("Demo data created (faculty@example.com, student1..6@example.com)")
