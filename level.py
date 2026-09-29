"""Pure text-level parsing and grid queries.

Coordinates in this module are always ``(x, y)`` tile coordinates, with the
origin at the map's top-left.  Only text before the first ``Legend:`` marker is
part of the map; explanatory legend rows are never interpreted as tiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping, TypeAlias


GridPosition: TypeAlias = tuple[int, int]

WALL = "#"
FLOOR = "."
PLAYER = "P"
BATTERY = "B"
DOOR = "D"
ENEMY = "E"
KEYCARD = "K"
EXIT = "X"
TERMINAL = "T"
CAMERA = "C"
EMP = "M"
HUNTER = "H"
BOSS = "W"

ALLOWED_TILES = frozenset(
    {
        WALL,
        FLOOR,
        PLAYER,
        BATTERY,
        DOOR,
        ENEMY,
        KEYCARD,
        EXIT,
        TERMINAL,
        CAMERA,
        EMP,
        HUNTER,
        BOSS,
    }
)
SPECIAL_TILES = (
    PLAYER,
    BATTERY,
    DOOR,
    ENEMY,
    KEYCARD,
    EXIT,
    TERMINAL,
    CAMERA,
    EMP,
    HUNTER,
    BOSS,
)


class LevelFormatError(ValueError):
    """Raised when level text cannot form a valid rectangular tile map."""


def _map_rows(text: str) -> tuple[str, ...]:
    """Extract map rows, stopping before a case-insensitive Legend marker."""

    lines = dedent(text).splitlines()
    legend_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().casefold() == "legend:"
        ),
        len(lines),
    )
    lines = lines[:legend_index]

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        raise LevelFormatError("level has no map rows before the Legend marker")
    if any(not line for line in lines):
        raise LevelFormatError("blank rows are not allowed inside the map")
    return tuple(lines)


@dataclass(frozen=True, slots=True)
class TileMap:
    """Validated level grid plus locations of all gameplay entities.

    Prefer :meth:`from_file` or :meth:`from_text` over constructing this class
    directly.  Walls and closed doors are non-walkable by default.
    """

    rows: tuple[str, ...]
    source: str | None = None
    _positions: Mapping[str, tuple[GridPosition, ...]] = field(
        init=False, repr=False, compare=False
    )
    _walls: frozenset[GridPosition] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.rows:
            raise LevelFormatError("level must contain at least one map row")

        width = len(self.rows[0])
        if width == 0:
            raise LevelFormatError("map rows cannot be empty")

        positions: dict[str, list[GridPosition]] = {
            symbol: [] for symbol in SPECIAL_TILES
        }
        walls: set[GridPosition] = set()

        for y, row in enumerate(self.rows):
            if len(row) != width:
                raise LevelFormatError(
                    f"map must be rectangular: row {y + 1} has width {len(row)}, "
                    f"expected {width}"
                )
            for x, symbol in enumerate(row):
                if symbol not in ALLOWED_TILES:
                    raise LevelFormatError(
                        f"unknown tile {symbol!r} at ({x}, {y}); "
                        f"allowed tiles are {''.join(sorted(ALLOWED_TILES))!r}"
                    )
                if symbol == WALL:
                    walls.add((x, y))
                elif symbol in positions:
                    positions[symbol].append((x, y))

        if len(positions[PLAYER]) != 1:
            raise LevelFormatError(
                "level must contain exactly one player spawn 'P'; "
                f"found {len(positions[PLAYER])}"
            )
        if len(positions[EXIT]) != 1:
            raise LevelFormatError(
                "level must contain exactly one exit 'X'; "
                f"found {len(positions[EXIT])}"
            )

        frozen_positions = {
            symbol: tuple(symbol_positions)
            for symbol, symbol_positions in positions.items()
        }
        object.__setattr__(self, "_positions", MappingProxyType(frozen_positions))
        object.__setattr__(self, "_walls", frozenset(walls))

    @classmethod
    def from_text(cls, text: str, *, source: str | None = None) -> "TileMap":
        """Parse and validate a map from level-file text."""

        if not isinstance(text, str):
            raise TypeError("level text must be a string")
        return cls(_map_rows(text), source=source)

    @classmethod
    def from_file(cls, path: str | Path) -> "TileMap":
        """Read a UTF-8 level file and return its validated map."""

        level_path = Path(path)
        return cls.from_text(
            level_path.read_text(encoding="utf-8"), source=str(level_path)
        )

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def player_spawn(self) -> GridPosition:
        return self._positions[PLAYER][0]

    @property
    def spawn_position(self) -> GridPosition:
        """Compatibility alias for :attr:`player_spawn`."""

        return self.player_spawn

    @property
    def enemy_spawns(self) -> tuple[GridPosition, ...]:
        return self._positions[ENEMY]

    @property
    def battery_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[BATTERY]

    @property
    def keycard_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[KEYCARD]

    @property
    def terminal_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[TERMINAL]

    @property
    def camera_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[CAMERA]

    @property
    def emp_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[EMP]

    @property
    def hunter_spawns(self) -> tuple[GridPosition, ...]:
        return self._positions[HUNTER]

    @property
    def boss_spawns(self) -> tuple[GridPosition, ...]:
        return self._positions[BOSS]

    @property
    def door_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[DOOR]

    @property
    def exit_positions(self) -> tuple[GridPosition, ...]:
        return self._positions[EXIT]

    @property
    def exit_position(self) -> GridPosition:
        return self._positions[EXIT][0]

    @property
    def walls(self) -> frozenset[GridPosition]:
        return self._walls

    @property
    def item_positions(self) -> Mapping[str, tuple[GridPosition, ...]]:
        """Immutable mapping of item tile symbols (``B``/``K``) to positions."""

        return MappingProxyType(
            {BATTERY: self.battery_positions, KEYCARD: self.keycard_positions}
        )

    def in_bounds(self, position: GridPosition) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, position: GridPosition) -> str:
        """Return a tile symbol, raising ``IndexError`` when out of bounds."""

        if not self.in_bounds(position):
            raise IndexError(f"tile position {position!r} is outside the level")
        x, y = position
        return self.rows[y][x]

    def is_walkable(
        self,
        position: GridPosition,
        opened_doors: Iterable[GridPosition] = (),
    ) -> bool:
        """Return whether a position may be entered.

        ``#`` is always blocked. ``D`` is blocked unless its position occurs in
        ``opened_doors``. Out-of-bounds positions are never walkable.
        """

        if not self.in_bounds(position):
            return False
        symbol = self.tile_at(position)
        if symbol == WALL:
            return False
        if symbol == DOOR and position not in opened_doors:
            return False
        return True

    def neighbors(
        self,
        position: GridPosition,
        opened_doors: Iterable[GridPosition] = (),
    ) -> tuple[GridPosition, ...]:
        """Return walkable four-way neighbors in deterministic order."""

        x, y = position
        candidates = ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))
        return tuple(
            candidate
            for candidate in candidates
            if self.is_walkable(candidate, opened_doors)
        )

    def iter_tiles(self) -> Iterator[tuple[GridPosition, str]]:
        """Yield ``((x, y), symbol)`` in row-major order."""

        for y, row in enumerate(self.rows):
            for x, symbol in enumerate(row):
                yield (x, y), symbol


# A concise alternate name for callers that think in terms of a game level.
Level = TileMap


def load_level(path: str | Path) -> TileMap:
    """Convenience wrapper around :meth:`TileMap.from_file`."""

    return TileMap.from_file(path)
