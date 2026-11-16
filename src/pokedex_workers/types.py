"""CSV row types this project owns.

Column order lives here until the scrapers package replaces the stubs in
`scrapers.py`. Fields are primitives so RQ can pickle a value as a job argument.
"""

from dataclasses import dataclass
import csv
from io import StringIO


def _line(values: list[object]) -> str:
    buffer = StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(values)
    return buffer.getvalue()


@dataclass(frozen=True)
class SeedCharacter:
    name: str
    character_id: str
    thumbnail_url: str
    initial_generation: int
    pokedex_id: str

    CSV_HEADER = "name,character_id,thumbnail_url,initial_generation,pokedex_id\n"

    def to_csv_line(self) -> str:
        return _line([self.name, self.character_id, self.thumbnail_url, self.initial_generation, self.pokedex_id])


@dataclass(frozen=True)
class GameCharacterMove:
    """One staged row of game_character_moves.csv.

    Only the id used as the staging dedupe key is fixed. Further columns are
    added when `build_character_moves` stops being a stub.
    """

    game_character_move_id: str

    CSV_HEADER = "game_character_move_id\n"

    def to_csv_line(self) -> str:
        return _line([self.game_character_move_id])


@dataclass(frozen=True)
class Move:
    """One row of moves.csv. Further columns are added when `list_moves` stops being a stub."""

    move_id: str

    CSV_HEADER = "move_id\n"

    def to_csv_line(self) -> str:
        return _line([self.move_id])


@dataclass(frozen=True)
class DexCharacter:
    dex_id: str
    character_id: str

    CSV_HEADER = "dex_id,character_id\n"

    def to_csv_line(self) -> str:
        return _line([self.dex_id, self.character_id])

    @property
    def dedupe_key(self) -> str:
        return f"{self.dex_id}:{self.character_id}"
