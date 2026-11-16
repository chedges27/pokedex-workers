"""Initial schema: pipeline runs, job runs, staged CSV rows, and dexes."""

from pathlib import Path

import sqlalchemy as sa
import yaml
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _dex_rows() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "dexes.yaml"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not loaded:
        return []
    return [{"dex_id": str(item["dex_id"]), "url": item["url"]} for item in loaded]


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=True),
        sa.Column("pending_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("s3_keys", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pipeline_runs_created_at", "pipeline_runs", ["created_at"])

    op.create_table(
        "job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rq_job_id", sa.Text(), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=True),
        sa.Column("queue_name", sa.Text(), nullable=False),
        sa.Column("job_name", sa.Text(), nullable=False),
        sa.Column("args", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("traceback", sa.Text(), nullable=True),
        sa.Column("output_key", sa.Text(), nullable=True),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("rq_job_id", name="uq_job_runs_rq_job_id"),
    )
    op.create_index("ix_job_runs_pipeline_run_id", "job_runs", ["pipeline_run_id"])
    op.create_index("ix_job_runs_status", "job_runs", ["status"])

    op.create_table(
        "staged_rows",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pipeline_runs.id"), nullable=False),
        sa.Column("dataset", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("csv_line", sa.Text(), nullable=False),
        sa.UniqueConstraint("pipeline_run_id", "dataset", "dedupe_key", "position", name="uq_staged_rows_dedupe"),
    )
    op.create_index("ix_staged_rows_pipeline_dataset", "staged_rows", ["pipeline_run_id", "dataset"])

    op.create_table(
        "dexes",
        sa.Column("dex_id", sa.Text(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
    )
    rows = _dex_rows()
    if rows:
        dexes = sa.table(
            "dexes",
            sa.column("dex_id", sa.Text()),
            sa.column("url", sa.Text()),
        )
        op.bulk_insert(dexes, rows)


def downgrade() -> None:
    op.drop_table("dexes")
    op.drop_index("ix_staged_rows_pipeline_dataset", table_name="staged_rows")
    op.drop_table("staged_rows")
    op.drop_index("ix_job_runs_status", table_name="job_runs")
    op.drop_index("ix_job_runs_pipeline_run_id", table_name="job_runs")
    op.drop_table("job_runs")
    op.drop_index("ix_pipeline_runs_created_at", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
