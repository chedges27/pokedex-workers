"""A shared pause before scrape jobs so extra workers do not all hit the site at once.

The slot is one Redis key. Each scrape job takes it, which holds the key for
SCRAPE_MIN_INTERVAL_SECONDS. The next job waits until the key expires. The
limit is per job: a library call may still make several HTTP requests inside
that one job. An interval of 0 disables the wait.
"""

import time

from redis import Redis

from pokedex_workers.settings import settings

_SLOT_KEY = "poke:scrape:slot"


def acquire(connection: Redis | None = None, interval_seconds: float | None = None) -> None:
    interval = settings.scrape_min_interval_seconds if interval_seconds is None else interval_seconds
    if interval <= 0:
        return

    client = connection if connection is not None else Redis.from_url(settings.redis_url)
    ttl_ms = max(int(interval * 1000), 1)
    while not client.set(_SLOT_KEY, "1", nx=True, px=ttl_ms):
        remaining = client.pttl(_SLOT_KEY)
        wait_ms = ttl_ms if remaining is None or remaining < 0 else remaining
        time.sleep(max(wait_ms, 1) / 1000)
