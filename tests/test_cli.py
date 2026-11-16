import pytest

from pokedex_workers.cli import main


def test_run_characters_is_later():
    with pytest.raises(SystemExit) as caught:
        main(["run", "characters", "--sample", "5"])
    assert caught.value.code == 2


def test_run_moves_is_later():
    with pytest.raises(SystemExit) as caught:
        main(["run", "moves"])
    assert caught.value.code == 2


def test_run_dexes_is_later():
    with pytest.raises(SystemExit) as caught:
        main(["run", "dexes"])
    assert caught.value.code == 2


def test_enqueue_single_jobs_are_later():
    with pytest.raises(SystemExit) as caught:
        main(["enqueue", "character-detail", "1"])
    assert caught.value.code == 2
    with pytest.raises(SystemExit) as caught:
        main(["enqueue", "character-moves", "1"])
    assert caught.value.code == 2
    with pytest.raises(SystemExit) as caught:
        main(["enqueue", "dex-character", "red-blue-yellow", "https://example.test/dex"])
    assert caught.value.code == 2


def test_status_rejects_a_non_uuid():
    with pytest.raises(SystemExit) as caught:
        main(["status", "not-a-uuid"])
    assert caught.value.code == 2
