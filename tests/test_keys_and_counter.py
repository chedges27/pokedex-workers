from unittest.mock import MagicMock
from uuid import uuid4

import fakeredis

from pokedex_workers.rate_limit import acquire
from pokedex_workers.s3 import adhoc_key, object_key, upload_bytes
from pokedex_workers.tracking import decrement_pending


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeConnection:
    def __init__(self, pending):
        self.pending = pending
        self.statement = None
        self.params = None

    def execute(self, statement, params=None):
        self.statement = str(statement)
        self.params = params
        return _Result(self.pending)


def test_full_run_key_stays_out_of_test_prefix():
    assert object_key("characters.csv", sample_size=None, prefix="pokemondb/") == "pokemondb/characters.csv"


def test_sample_run_uses_test_prefix():
    assert object_key("moves.csv", sample_size=5, prefix="pokemondb/") == "pokemondb/test/moves.csv"


def test_adhoc_key_is_under_test():
    assert adhoc_key("character-detail", "abc", prefix="pokemondb/") == "pokemondb/test/adhoc/character-detail/abc.csv"


def test_upload_bytes_puts_the_object():
    client = MagicMock()
    assert upload_bytes("pokemondb/moves.csv", b"id\n", client=client) == "pokemondb/moves.csv"
    client.put_object.assert_called_once_with(Bucket="pokedex", Key="pokemondb/moves.csv", Body=b"id\n")


def test_decrement_pending_counts_a_success():
    connection = FakeConnection(pending=0)
    assert decrement_pending(connection, uuid4(), succeeded=True) == 0
    assert "pending_jobs = pending_jobs - 1" in connection.statement
    assert connection.params["succeeded"] == 1
    assert connection.params["failed"] == 0


def test_decrement_pending_counts_a_failure():
    connection = FakeConnection(pending=2)
    assert decrement_pending(connection, uuid4(), succeeded=False) == 2
    assert connection.params["succeeded"] == 0
    assert connection.params["failed"] == 1


def test_acquire_does_nothing_when_disabled():
    connection = MagicMock()
    acquire(connection=connection, interval_seconds=0)
    connection.set.assert_not_called()


def test_acquire_takes_the_slot():
    connection = fakeredis.FakeRedis()
    acquire(connection=connection, interval_seconds=1)
    assert connection.get("poke:scrape:slot") == b"1"


def test_acquire_waits_until_the_slot_frees(monkeypatch):
    connection = fakeredis.FakeRedis()
    connection.set("poke:scrape:slot", "1", px=5000)
    slept = []

    def release(seconds):
        slept.append(seconds)
        connection.delete("poke:scrape:slot")

    monkeypatch.setattr("pokedex_workers.rate_limit.time.sleep", release)
    acquire(connection=connection, interval_seconds=1)
    assert slept
    assert connection.get("poke:scrape:slot") == b"1"
