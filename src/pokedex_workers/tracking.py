"""RQ job class and worker that record every run in job_runs.

Job functions do not touch the database. enqueue_tracked inserts the queued
row, TrackingWorker marks it started, and TrackedJob marks it finished or
failed. When the job belongs to a pipeline run, a terminal result also
decrements pipeline_runs.pending_jobs.

Enqueueing the assemble job when that counter hits zero arrives with the
characters pipeline. This module only returns the new pending count.
"""

from datetime import datetime, timezone
import traceback as traceback_module
from uuid import UUID, uuid4

from redis import Redis
from rq import Callback, Queue, SimpleWorker, Worker
from rq.job import Job
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from pokedex_workers.db import session_scope
from pokedex_workers.models import JobRun

QUEUES = ("pipelines", "characters", "character_moves", "moves", "dexes")

_DECREMENT = text(
    """
    UPDATE pipeline_runs
    SET pending_jobs = pending_jobs - 1,
        jobs_succeeded = jobs_succeeded + :succeeded,
        jobs_failed = jobs_failed + :failed
    WHERE id = :id
    RETURNING pending_jobs
    """
)


def decrement_pending(connection, pipeline_run_id: UUID, *, succeeded: bool) -> int:
    """Apply one terminal child outcome. Returns the pending count left after it.

    `connection` is anything with execute(), including a Session or a test double.
    The caller commits.
    """
    result = connection.execute(
        _DECREMENT,
        {
            "id": pipeline_run_id,
            "succeeded": 1 if succeeded else 0,
            "failed": 0 if succeeded else 1,
        },
    )
    return int(result.scalar_one())


def _row(session: Session, rq_job_id: str) -> JobRun | None:
    return session.scalar(select(JobRun).where(JobRun.rq_job_id == rq_job_id))


def mark_started(job: Job) -> None:
    with session_scope() as session:
        row = _row(session, job.id)
        if row is None or row.status in {"finished", "failed"}:
            return
        row.status = "started"
        if row.started_at is None:
            row.started_at = datetime.now(timezone.utc)


def _finish(job: Job, *, succeeded: bool, error: str | None = None, formatted: str | None = None) -> None:
    with session_scope() as session:
        row = _row(session, job.id)
        if row is None:
            return
        row.status = "finished" if succeeded else "failed"
        row.finished_at = datetime.now(timezone.utc)
        row.error = error
        row.traceback = formatted
        if row.pipeline_run_id is not None:
            decrement_pending(session, row.pipeline_run_id, succeeded=succeeded)


def mark_finished(job: Job) -> None:
    _finish(job, succeeded=True)


def mark_failed(job: Job, exc_value: BaseException, traceback) -> None:
    retries_left = int(getattr(job, "retries_left", 0) or 0)
    if retries_left:
        return
    formatted = "".join(traceback_module.format_exception(type(exc_value), exc_value, traceback))
    _finish(job, succeeded=False, error=str(exc_value), formatted=formatted)


def record_success(job: Job, connection, result) -> None:
    """RQ success callback. RQ stores this function's import path on the job."""
    del connection, result
    mark_finished(job)


def record_failure(job: Job, connection, exc_type, exc_value, traceback) -> None:
    """RQ failure callback. A retry still calls this; mark_failed ignores it while retries remain."""
    del connection, exc_type
    if exc_value is None:
        exc_value = RuntimeError("job failed")
    mark_failed(job, exc_value, traceback)


class TrackedJob(Job):
    """Job class the worker uses so bookkeeping stays on one type.

    RQ 3 runs the callbacks registered at enqueue time. These methods call the
    same recorders for anything that still invokes them on the job.
    """

    def on_success(self, connection, result):
        record_success(self, connection, result)

    def on_failure(self, connection, exc_type, exc_value, traceback):
        record_failure(self, connection, exc_type, exc_value, traceback)


class _Tracking:
    job_class = TrackedJob

    def prepare_job_execution(self, job, *args, **kwargs):
        mark_started(job)
        return super().prepare_job_execution(job, *args, **kwargs)


class TrackingWorker(_Tracking, Worker):
    pass


class TrackingSimpleWorker(_Tracking, SimpleWorker):
    pass


def enqueue_tracked(
    func,
    *,
    queue_name: str,
    job_name: str,
    connection: Redis,
    args: tuple = (),
    kwargs: dict | None = None,
    pipeline_run_id: UUID | None = None,
    timeout: int = 30,
    retry=None,
) -> Job:
    """Insert a queued job_runs row, then enqueue. The row exists before a worker can take the job."""
    payload = kwargs or {}
    rq_job_id = str(uuid4())
    with session_scope() as session:
        session.add(
            JobRun(
                rq_job_id=rq_job_id,
                pipeline_run_id=pipeline_run_id,
                queue_name=queue_name,
                job_name=job_name,
                args={"args": list(args), "kwargs": payload},
                status="queued",
            )
        )

    queue = Queue(queue_name, connection=connection, job_class=TrackedJob)
    return queue.enqueue(
        func,
        *args,
        **payload,
        job_id=rq_job_id,
        job_timeout=timeout,
        retry=retry,
        result_ttl=500,
        on_success=Callback(record_success),
        on_failure=Callback(record_failure),
    )
