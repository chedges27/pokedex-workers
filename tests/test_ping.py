"""Ping through a synchronous worker against Postgres and fakeredis."""

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fakeredis import FakeRedis
from sqlalchemy import select

from pokedex_workers.db import session_scope
from pokedex_workers.jobs.ping import ping
from pokedex_workers.models import JobRun, PipelineRun
from pokedex_workers.tracking import TrackedJob, TrackingSimpleWorker, decrement_pending, enqueue_tracked


pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL is not set")


@pytest.fixture(scope="module")
def migrated():
    command.upgrade(Config("alembic.ini"), "head")


def test_ping_job_run_reaches_finished(migrated):
    redis = FakeRedis()
    job = enqueue_tracked(ping, queue_name="pipelines", job_name="ping", connection=redis)
    assert job.id

    with session_scope() as session:
        queued = session.scalar(select(JobRun).where(JobRun.rq_job_id == job.id))
        assert queued.status == "queued"
        assert queued.pipeline_run_id is None
        assert queued.job_name == "ping"

    TrackingSimpleWorker(["pipelines"], connection=redis).work(burst=True)

    with session_scope() as session:
        finished = session.scalar(select(JobRun).where(JobRun.rq_job_id == job.id))
        assert finished.status == "finished"
        assert finished.started_at is not None
        assert finished.finished_at is not None
        assert finished.error is None
    assert TrackedJob.fetch(job.id, connection=redis).return_value() == "pong"


def test_status_reports_a_missing_pipeline(migrated, capsys):
    from pokedex_workers.cli import main

    missing = uuid4()
    with pytest.raises(SystemExit) as caught:
        main(["status", str(missing)])
    assert caught.value.code == 1
    assert str(missing) in capsys.readouterr().out


def test_decrement_pending_updates_postgres(migrated):
    pipeline_id = uuid4()
    with session_scope() as session:
        session.add(
            PipelineRun(
                id=pipeline_id,
                name="characters",
                status="running",
                pending_jobs=2,
                jobs_total=2,
            )
        )

    with session_scope() as session:
        pending = decrement_pending(session, pipeline_id, succeeded=True)
        assert pending == 1

    with session_scope() as session:
        pending = decrement_pending(session, pipeline_id, succeeded=False)
        assert pending == 0
        row = session.get(PipelineRun, pipeline_id)
        assert row.jobs_succeeded == 1
        assert row.jobs_failed == 1
        assert row.pending_jobs == 0
