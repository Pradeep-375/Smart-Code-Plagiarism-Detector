"""All relational models. SQLAlchemy 2.0 typed declarative style."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, BigInteger, Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Table,
    Text, UniqueConstraint, Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RoleName(str, enum.Enum):
    admin = "admin"
    faculty = "faculty"
    student = "student"


class SubmissionStatus(str, enum.Enum):
    uploaded = "uploaded"
    queued = "queued"
    analyzing = "analyzing"
    analyzed = "analyzed"
    failed = "failed"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    dismissed = "dismissed"  # reviewed, no concern
    flagged = "flagged"  # needs further investigation
    confirmed = "confirmed"  # faculty confirmed copying


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


group_members = Table(
    "group_members", Base.metadata,
    Column("group_id", ForeignKey("assignment_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(200), default="")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    organization_id: Mapped[str | None] = mapped_column(String(60))  # roll number / employee id
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[Role] = relationship(lazy="joined")

    @property
    def role_name(self) -> str:
        return self.role.name


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class ProgrammingLanguage(Base):
    __tablename__ = "programming_languages"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)  # engine key, e.g. "cpp"
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    extensions: Mapped[str] = mapped_column(String(100), nullable=False)  # ".cpp,.cc,.hpp"
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Assignment(TimestampMixin, Base):
    __tablename__ = "assignments"
    __table_args__ = (Index("ix_assignments_creator_created", "created_by", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    language_key: Mapped[str] = mapped_column(String(30), nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_group: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    review_threshold: Mapped[float | None] = mapped_column(Float)
    high_threshold: Mapped[float | None] = mapped_column(Float)
    show_results_to_students: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    groups: Mapped[list["AssignmentGroup"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")
    reference_files: Mapped[list["ReferenceFile"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class ReferenceFile(Base):
    """Starter / template code: matches against it are ignored by the detector."""
    __tablename__ = "reference_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    assignment: Mapped[Assignment] = relationship(back_populates="reference_files")


class AssignmentGroup(Base):
    __tablename__ = "assignment_groups"
    __table_args__ = (UniqueConstraint("assignment_id", "name", name="uq_group_name_per_assignment"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    assignment: Mapped[Assignment] = relationship(back_populates="groups")
    members: Mapped[list[User]] = relationship(secondary=group_members)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", "version", name="uq_submission_version"),
        Index("ix_submissions_assignment_status", "assignment_id", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("assignment_groups.id", ondelete="SET NULL"))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.uploaded, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("submissions.id", ondelete="SET NULL"))
    max_similarity: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(Text, default="")

    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    student: Mapped[User] = relationship(foreign_keys=[student_id])
    group: Mapped[AssignmentGroup | None] = relationship()
    files: Mapped[list["SubmissionFile"]] = relationship(back_populates="submission", cascade="all, delete-orphan", order_by="SubmissionFile.filename")


class SubmissionFile(Base):
    __tablename__ = "submission_files"
    __table_args__ = (UniqueConstraint("submission_id", "filename", name="uq_file_per_submission"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # sanitised relative path
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)  # random name on disk
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    language_key: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    submission: Mapped[Submission] = relationship(back_populates="files")


class CodeFingerprint(Base):
    __tablename__ = "code_fingerprints"
    __table_args__ = (Index("ix_fp_hash", "hash"), Index("ix_fp_submission", "submission_id"))
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, nullable=False)
    include_history: Mapped[bool] = mapped_column(Boolean, default=False)
    include_other_assignments: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    total_pairs: Mapped[int] = mapped_column(Integer, default=0)
    done_pairs: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def progress(self) -> float:
        if self.status == JobStatus.completed:
            return 1.0
        return round(self.done_pairs / self.total_pairs, 4) if self.total_pairs else 0.0


class SimilarityResult(Base):
    __tablename__ = "similarity_results"
    __table_args__ = (
        UniqueConstraint("job_id", "submission_a_id", "submission_b_id", name="uq_pair_per_job"),
        CheckConstraint("submission_a_id <> submission_b_id", name="ck_distinct_submissions"),
        CheckConstraint("overall >= 0 AND overall <= 1", name="ck_overall_range"),
        Index("ix_results_assignment_overall", "assignment_id", "overall"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    submission_a_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    submission_b_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    overall: Mapped[float] = mapped_column(Float, nullable=False)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_label: Mapped[str] = mapped_column(String(10), default="low")
    risk_level: Mapped[str] = mapped_column(String(10), default="low")
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    explanations: Mapped[list] = mapped_column(JSON, default=list)
    ml_probability: Mapped[float | None] = mapped_column(Float)
    review_status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.pending, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str] = mapped_column(Text, default="")
    override_score: Mapped[float | None] = mapped_column(Float)  # faculty adjusted similarity (0-1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submission_a: Mapped[Submission] = relationship(foreign_keys=[submission_a_id])
    submission_b: Mapped[Submission] = relationship(foreign_keys=[submission_b_id])
    segments: Mapped[list["MatchedSegment"]] = relationship(back_populates="result", cascade="all, delete-orphan")

    @property
    def effective_score(self) -> float:
        return self.override_score if self.override_score is not None else self.overall


class MatchedSegment(Base):
    __tablename__ = "matched_segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("similarity_results.id", ondelete="CASCADE"), index=True)
    a_file: Mapped[str] = mapped_column(String(255), default="")
    b_file: Mapped[str] = mapped_column(String(255), default="")
    a_start_line: Mapped[int] = mapped_column(Integer)
    a_end_line: Mapped[int] = mapped_column(Integer)
    b_start_line: Mapped[int] = mapped_column(Integer)
    b_end_line: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int] = mapped_column(Integer)
    result: Mapped[SimilarityResult] = relationship(back_populates="segments")


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # pair | assignment
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[int | None] = mapped_column(ForeignKey("similarity_results.id", ondelete="SET NULL"))
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str | None] = mapped_column(String(300))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_created", "created_at"), Index("ix_audit_action", "action"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    user: Mapped[User | None] = relationship()
