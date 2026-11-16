"""Postgres tables for pipeline runs, job runs, staged CSV rows, and dexes."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    s3_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    rq_job_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    pipeline_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=True)
    queue_name: Mapped[str] = mapped_column(Text, nullable=False)
    job_name: Mapped[str] = mapped_column(Text, nullable=False)
    args: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StagedRow(Base):
    __tablename__ = "staged_rows"
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "dataset", "dedupe_key", "position", name="uq_staged_rows_dedupe"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False)
    dataset: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    csv_line: Mapped[str] = mapped_column(Text, nullable=False)


class Dex(Base):
    __tablename__ = "dexes"

    dex_id: Mapped[str] = mapped_column(Text, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
