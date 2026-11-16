# pokedex-workers

RQ workers that run pokedex pipelines, record every job in Postgres, and upload CSV files to S3. Scraping stays in `pokemondb_net_scrapers`. This repo calls it through `pokedex_workers.scrapers`, which currently returns sample rows.

Phase 1 proves the skeleton with one job, `ping`. The characters, moves, and dex pipelines are registered on the CLI and are not implemented yet.

## Local setup

Docker Compose runs Redis, Postgres, MinIO, rq-dashboard, a one-shot migration, and a worker. Copy the env file if you want to run the CLI on the host against those ports:

```
copy .env.example .env
docker compose up --build
```

Scale the all-queue worker:

```
docker compose up --build --scale worker=3
```

To scale one queue on its own, start the split profile instead of adding more copies of `worker` (those copies listen to every queue):

```
docker compose --profile split up --build --scale worker-characters=3
```

The split services are `worker-pipelines`, `worker-characters`, `worker-character-moves`, `worker-moves`, and `worker-dexes`.

rq-dashboard is at [http://localhost:9181](http://localhost:9181). MinIO's API is on port 9000 and the bucket is `pokedex`.

## Ping

With the stack up:

```
pokedex-workers run ping
```

`enqueue ping` puts the same job on the `pipelines` queue. The worker records a `job_runs` row and the dashboard shows the job. Confirm the row:

```
docker compose exec postgres psql -U pokedex -d pokedex_workers -c "select rq_job_id, job_name, status, started_at, finished_at from job_runs order by enqueued_at desc limit 5;"
```

`pokedex-workers status <pipeline_run_id>` prints a pipeline run, or says it is missing. Ping does not create a pipeline run.

These commands exit with a later-phase message until their pipelines exist:

```
pokedex-workers run characters --sample 5
pokedex-workers run moves
pokedex-workers run dexes
pokedex-workers enqueue character-detail <character_id>
pokedex-workers enqueue character-moves <character_id>
pokedex-workers enqueue dex-character <dex_id> <url>
```

## Tests

```
pip install -e ".[dev]"
```

Set `DATABASE_URL` to a Postgres database (Compose publishes one on `localhost:5432`) and run:

```
pytest
```

Queue tests use fakeredis. Nothing in the tests contacts pokemondb.net. Without `DATABASE_URL`, the ping test is skipped and the other tests still run.

## Configuration

See `.env.example`. `S3_ENDPOINT_URL` is optional so MinIO works locally. `S3_PREFIX` is prepended to every object key. `SCRAPE_MIN_INTERVAL_SECONDS` is the shared pause before a scrape job (`0` turns it off). `WORKER_QUEUES` is the queue list for a worker process.
