"""Stand-ins for pokemondb_net_scrapers.

Jobs call these functions and nothing else in the scrapers package. Each one
returns fixed sample objects. Replace the body, not the signature.
"""

from pokedex_workers.types import DexCharacter, GameCharacterMove, Move, SeedCharacter

_SAMPLE_SEED = SeedCharacter(
    name="Bulbasaur",
    character_id="1",
    thumbnail_url="https://example.test/bulbasaur.png",
    initial_generation=1,
    pokedex_id="0001",
)


def list_seed_character(sample_size: int | None) -> list[SeedCharacter]:
    """Stub. Replace with the pokemondb_net_scrapers call that lists seed characters."""
    rows = [_SAMPLE_SEED]
    if sample_size is None:
        return rows
    return rows[:sample_size]


def build_character(seed: SeedCharacter) -> list[SeedCharacter]:
    """Stub. Replace with the pokemondb_net_scrapers call that builds one character.

    Staged for characters.csv.
    """
    return [seed]


def build_character_moves(seed: SeedCharacter) -> list[GameCharacterMove]:
    """Stub. Replace with the pokemondb_net_scrapers call that builds one character's moves.

    Staged for game_character_moves.csv.
    """
    return [GameCharacterMove(game_character_move_id=f"{seed.character_id}-1")]


def list_moves() -> list[Move]:
    """Stub. Replace with the pokemondb_net_scrapers call that lists moves.

    Uploaded as moves.csv.
    """
    return [Move(move_id="1")]


def list_dex_characters(dex_id: str, url: str) -> list[DexCharacter]:
    """Stub. Replace with the pokemondb_net_scrapers call that lists one dex's characters.

    Staged for dex_characters.csv. `url` is accepted so the real call can fetch
    that dex; the stub does not use it.
    """
    del url
    return [DexCharacter(dex_id=dex_id, character_id="1")]
