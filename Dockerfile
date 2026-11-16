FROM python:3.14-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY alembic ./alembic
COPY dexes.yaml ./
RUN printf '%s\n' '#!/bin/sh' 'set -eu' 'exec rq worker --url "$REDIS_URL" --worker-class pokedex_workers.tracking.TrackingWorker $WORKER_QUEUES' > /app/worker.sh \
    && chmod +x /app/worker.sh

CMD ["/app/worker.sh"]
