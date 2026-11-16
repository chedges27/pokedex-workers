"""S3 keys and uploads.

A full run writes `{prefix}{filename}`. A run with sample_size set, and every
job that has no pipeline run, writes under `{prefix}test/` so it cannot
replace a full run.
"""

import boto3

from pokedex_workers.settings import settings


def _join(prefix: str, *parts: str) -> str:
    head = prefix.strip("/")
    tail = "/".join(part.strip("/") for part in parts if part != "")
    if head and tail:
        return f"{head}/{tail}"
    return head or tail


def object_key(filename: str, *, sample_size: int | None = None, prefix: str | None = None) -> str:
    root = settings.s3_prefix if prefix is None else prefix
    if sample_size is not None:
        return _join(root, "test", filename)
    return _join(root, filename)


def adhoc_key(job_name: str, rq_job_id: str, *, prefix: str | None = None) -> str:
    root = settings.s3_prefix if prefix is None else prefix
    return _join(root, "test", "adhoc", job_name, f"{rq_job_id}.csv")


def s3_client():
    kwargs = {"region_name": settings.aws_default_region}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def upload_bytes(key: str, body: bytes, *, client=None) -> str:
    (client or s3_client()).put_object(Bucket=settings.s3_bucket, Key=key, Body=body)
    return key
