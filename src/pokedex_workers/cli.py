"""Command line for enqueueing work and reading pipeline status.

`run characters`, `run moves`, `run dexes`, and the single-job `enqueue`
commands are registered so the surface is visible. They do not run yet.
"""

import argparse
from uuid import UUID

from redis import Redis
from sqlalchemy import select

from pokedex_workers.db import session_scope
from pokedex_workers.jobs.ping import ping
from pokedex_workers.models import PipelineRun
from pokedex_workers.settings import settings
from pokedex_workers.tracking import enqueue_tracked


def _later(what: str) -> int:
    print(f"{what} arrives in a later phase.")
    return 2


def _enqueue_ping() -> int:
    job = enqueue_tracked(
        ping,
        queue_name="pipelines",
        job_name="ping",
        connection=Redis.from_url(settings.redis_url),
        timeout=30,
    )
    print(f"enqueued ping {job.id} on pipelines")
    return 0


def _status(pipeline_run_id: str) -> int:
    try:
        parsed = UUID(pipeline_run_id)
    except ValueError:
        print(f"Not a pipeline run id: {pipeline_run_id}")
        return 2

    with session_scope() as session:
        row = session.scalar(select(PipelineRun).where(PipelineRun.id == parsed))
        if row is None:
            print(f"No pipeline run {pipeline_run_id}")
            return 1
        print(f"id: {row.id}")
        print(f"name: {row.name}")
        print(f"status: {row.status}")
        print(f"sample_size: {row.sample_size}")
        print(f"pending_jobs: {row.pending_jobs}")
        print(f"jobs_total: {row.jobs_total}")
        print(f"jobs_succeeded: {row.jobs_succeeded}")
        print(f"jobs_failed: {row.jobs_failed}")
        print(f"s3_keys: {row.s3_keys}")
        if row.error:
            print(f"error: {row.error}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pokedex-workers")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="start a pipeline, or the ping job")
    run_sub = run.add_subparsers(dest="pipeline", required=True)
    run_ping = run_sub.add_parser("ping", help="enqueue a trivial job")
    run_ping.set_defaults(func=lambda args: _enqueue_ping())
    for name in ("characters", "moves", "dexes"):
        command = run_sub.add_parser(name)
        command.add_argument("--sample", type=int, default=None)
        command.set_defaults(func=lambda args, name=name: _later(f"run {name}"))

    enqueue = sub.add_parser("enqueue", help="enqueue one job with no parent pipeline")
    enqueue_sub = enqueue.add_subparsers(dest="job", required=True)
    enqueue_ping = enqueue_sub.add_parser("ping")
    enqueue_ping.set_defaults(func=lambda args: _enqueue_ping())
    detail = enqueue_sub.add_parser("character-detail")
    detail.add_argument("character_id")
    detail.set_defaults(func=lambda args: _later("enqueue character-detail"))
    moves = enqueue_sub.add_parser("character-moves")
    moves.add_argument("character_id")
    moves.set_defaults(func=lambda args: _later("enqueue character-moves"))
    dex = enqueue_sub.add_parser("dex-character")
    dex.add_argument("dex_id")
    dex.add_argument("url")
    dex.set_defaults(func=lambda args: _later("enqueue dex-character"))

    status = sub.add_parser("status", help="print one pipeline run")
    status.add_argument("pipeline_run_id")
    status.set_defaults(func=lambda args: _status(args.pipeline_run_id))

    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))
