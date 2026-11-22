import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(UTC)


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class Installation(Base):
    __tablename__ = "installation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    initialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now
    )


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    external_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    full_name: Mapped[str] = mapped_column(String(200))
    workflow_ids: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    stats_version: Mapped[int] = mapped_column(Integer, default=0)


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(Integer)


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_run_id", "attempt"),
        Index("ix_runs_cursor", "repository_id", "created_at", "id"),
        Index("ix_runs_history", "pull_request_id", "github_created_at", "attempt"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    pull_request_id: Mapped[str] = mapped_column(
        ForeignKey("pull_requests.id", ondelete="CASCADE")
    )
    github_run_id: Mapped[int] = mapped_column(BigInteger)
    attempt: Mapped[int] = mapped_column(
        Integer
    )  # 0 = legacy v1 unknown, NEVER a real attempt 1
    head_sha: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(16))
    payload_hash: Mapped[str] = mapped_column(String(64))
    finding_count: Mapped[int] = mapped_column(Integer, default=0)
    analysis_status: Mapped[str] = mapped_column(String(32))
    github_status: Mapped[str] = mapped_column(String(32), default="unknown")
    github_conclusion: Mapped[str | None] = mapped_column(String(32), nullable=True)
    collection_status: Mapped[str] = mapped_column(String(32), default="available")
    github_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    raw_report: Mapped[dict] = mapped_column(JSON)
    ui: Mapped[dict] = mapped_column(JSON)


class Stage(Base):
    __tablename__ = "stages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict] = mapped_column(JSON)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    data: Mapped[dict] = mapped_column(JSON)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    requirement_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSON)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    evidence_key: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(32))
    data: Mapped[dict] = mapped_column(JSON)


class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), unique=True
    )
    calls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_recovery", "status", "lease_until", "next_retry_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_id: Mapped[int] = mapped_column(BigInteger)
    run_attempt: Mapped[int] = mapped_column(Integer)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    delivery_seq: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        UniqueConstraint("job_id", "seq"),
        Index("ix_outbox_dispatch", "sent_at", "available_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    send_attempts: Mapped[int] = mapped_column(Integer, default=0)


class SyncCursor(Base):
    __tablename__ = "sync_cursors"
    repository_id: Mapped[str] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True
    )
    last_scan_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Audit(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
