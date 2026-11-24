from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..core.security import validate_password_strength

RoleLiteral = Literal["admin", "faculty", "student"]
ReviewLiteral = Literal["pending", "dismissed", "flagged", "confirmed"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / users ----------
class _AccountIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str
    organization_id: str | None = Field(default=None, max_length=60)

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class RegisterIn(_AccountIn):
    """Public self-registration. ``admin`` is deliberately not an allowed value: admins are never self-service."""
    role: Literal["student", "faculty"] = "student"
    faculty_code: str | None = Field(default=None, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(ORM):
    id: int
    email: EmailStr
    full_name: str
    role_name: str
    is_active: bool
    organization_id: str | None = None
    email_notifications: bool = True
    created_at: datetime
    last_login_at: datetime | None = None


class UserCreateIn(_AccountIn):
    role: RoleLiteral = "student"


class UserUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: RoleLiteral | None = None
    is_active: bool | None = None
    organization_id: str | None = None


class ProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    organization_id: str | None = Field(default=None, max_length=60)
    email_notifications: bool | None = None


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


# ---------- assignments ----------
class AssignmentIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=10000)
    language_key: str
    deadline: datetime | None = None
    is_group: bool = False
    is_published: bool = True
    review_threshold: float | None = Field(default=None, ge=0, le=1)
    high_threshold: float | None = Field(default=None, ge=0, le=1)
    show_results_to_students: bool = False


class AssignmentUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    language_key: str | None = None
    deadline: datetime | None = None
    is_group: bool | None = None
    is_published: bool | None = None
    review_threshold: float | None = Field(default=None, ge=0, le=1)
    high_threshold: float | None = Field(default=None, ge=0, le=1)
    show_results_to_students: bool | None = None


class AssignmentOut(ORM):
    id: int
    title: str
    description: str
    language_key: str
    deadline: datetime | None
    is_group: bool
    is_published: bool
    created_by: int
    review_threshold: float | None
    high_threshold: float | None
    show_results_to_students: bool
    created_at: datetime
    submission_count: int = 0
    my_submission_count: int | None = None


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    member_ids: list[int] = []


class GroupOut(BaseModel):
    id: int
    name: str
    members: list[UserOut]


# ---------- submissions ----------
class SubmissionFileOut(ORM):
    id: int
    filename: str
    size_bytes: int
    sha256: str
    language_key: str


class SubmissionOut(ORM):
    id: int
    assignment_id: int
    assignment_title: str | None = None
    student_id: int
    student_name: str | None = None
    student_email: str | None = None
    group_id: int | None
    version: int
    status: str
    submitted_at: datetime
    is_late: bool
    duplicate_of_id: int | None
    max_similarity: float | None = None
    files: list[SubmissionFileOut] = []


class FileContentOut(BaseModel):
    id: int
    filename: str
    language_key: str
    content: str


# ---------- analysis ----------
class AnalyzeIn(BaseModel):
    include_history: bool = False  # compare against the same teacher's earlier assignments (same language)
    include_other_assignments: bool = False  # admin-only: compare against every assignment
    weights: dict[str, float] | None = None
    review_threshold: float | None = Field(default=None, ge=0, le=1)
    high_threshold: float | None = Field(default=None, ge=0, le=1)


class JobOut(ORM):
    id: int
    assignment_id: int
    status: str
    progress: float
    total_pairs: int
    done_pairs: int
    error: str | None
    include_history: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SegmentOut(ORM):
    id: int
    a_file: str
    b_file: str
    a_start_line: int
    a_end_line: int
    b_start_line: int
    b_end_line: int
    token_count: int


class ResultSummary(BaseModel):
    id: int
    assignment_id: int
    assignment_title: str | None = None
    submission_a_id: int
    submission_b_id: int
    student_a: str
    student_b: str
    overall: float
    effective_score: float
    risk_level: str
    confidence_label: str
    is_duplicate: bool
    review_status: str
    job_id: int


class ResultDetail(ResultSummary):
    scores: dict[str, float]
    confidence: float
    explanations: list[str]
    ml_probability: float | None
    review_notes: str
    override_score: float | None
    reviewed_at: datetime | None
    reviewer_name: str | None = None
    segments: list[SegmentOut]
    files_a: list[FileContentOut]
    files_b: list[FileContentOut]
    disclaimer: str


class ReviewIn(BaseModel):
    review_status: ReviewLiteral
    notes: str = Field(default="", max_length=5000)
    override_score: float | None = Field(default=None, ge=0, le=1)


class CompareIn(BaseModel):
    submission_a_id: int
    submission_b_id: int


class StudentFeedbackOut(BaseModel):
    submission_id: int
    status: str
    results_visible: bool
    max_similarity: float | None = None
    band: str | None = None  # low | review | high
    message: str


# ---------- misc ----------
class NotificationOut(ORM):
    id: int
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    user_email: str | None
    action: str
    entity_type: str | None
    entity_id: int | None
    ip_address: str | None
    details: dict
    created_at: datetime


class LanguageIn(BaseModel):
    key: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_+-]+$")
    name: str = Field(min_length=1, max_length=60)
    extensions: str = Field(max_length=100)
    enabled: bool = True


class LanguageOut(ORM):
    id: int
    key: str
    name: str
    extensions: str
    enabled: bool


class DetectionSettingsIn(BaseModel):
    weights: dict[str, float] | None = None
    review_threshold: float | None = Field(default=None, ge=0, le=1)
    high_threshold: float | None = Field(default=None, ge=0, le=1)


TokenOut.model_rebuild()
