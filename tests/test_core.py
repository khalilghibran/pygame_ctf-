"""Unit tests for the pure map, navigation, and visibility core."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from level import LevelFormatError, TileMap
from pathfinding import astar, has_line_of_sight, supercover_line


VALID_LEVEL = """
#######
#P.B..#
#.#D#.#
#E.K.X#
#######

Legend:
# deliberately not a map row
P player start
"""


class TileMapTests(unittest.TestCase):
    def test_valid_level_parses_only_rows_before_legend(self) -> None:
        level = TileMap.from_text(VALID_LEVEL)

        self.assertEqual(level.dimensions, (7, 5))
        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.enemy_spawns, ((1, 3),))
        self.assertEqual(level.battery_positions, ((3, 1),))
        self.assertEqual(level.keycard_positions, ((3, 3),))
        self.assertEqual(level.door_positions, ((3, 2),))
        self.assertEqual(level.exit_position, (5, 3))
        self.assertEqual(level.item_positions["B"], ((3, 1),))
        self.assertTrue(level.is_walkable((1, 1)))
        self.assertFalse(level.is_walkable((0, 0)))
        self.assertFalse(level.is_walkable((3, 2)))
        self.assertTrue(level.is_walkable((3, 2), opened_doors={(3, 2)}))
        self.assertFalse(level.is_walkable((-1, 1)))

    def test_level_can_be_loaded_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "level.txt")
            path.write_text(VALID_LEVEL, encoding="utf-8")
            level = TileMap.from_file(path)

        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.source, str(path))

    def test_malformed_levels_are_rejected(self) -> None:
        malformed = {
            "empty": "Legend:\n# wall\n",
            "ragged": "#####\n#P.X#\n####\n",
            "unknown symbol": "#####\n#P@X#\n#####\n",
            "missing player": "#####\n#..X#\n#####\n",
            "duplicate player": "######\n#PP.X#\n######\n",
            "missing exit": "#####\n#P..#\n#####\n",
            "duplicate exit": "######\n#P.XX#\n######\n",
        }
        for label, text in malformed.items():
            with self.subTest(label=label):
                with self.assertRaises(LevelFormatError):
                    TileMap.from_text(text)


class AStarTests(unittest.TestCase):
    def test_astar_finds_shortest_path_around_obstacles(self) -> None:
        blocked = {(1, 0), (1, 1), (1, 2)}

        def walkable(position: tuple[int, int]) -> bool:
            x, y = position
            return 0 <= x < 5 and 0 <= y < 5 and position not in blocked

        path = astar((0, 0), (4, 0), walkable)

        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (4, 0))
        self.assertEqual(len(path), 11)
        self.assertTrue(all(walkable(position) for position in path))
        self.assertTrue(
            all(
                abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
                for a, b in zip(path, path[1:])
            )
        )

    def test_astar_returns_empty_when_goal_is_sealed(self) -> None:
        walkable_cells = {(0, 0), (1, 0), (2, 0), (2, 1)}
        self.assertEqual(
            astar((0, 0), (2, 2), walkable_cells.__contains__), []
        )


class LineOfSightTests(unittest.TestCase):
    def test_unblocked_and_blocked_line_of_sight(self) -> None:
        bounds = {(x, y) for x in range(5) for y in range(3)}
        self.assertTrue(
            has_line_of_sight((0, 1), (4, 1), bounds.__contains__)
        )

        transparent = bounds - {(2, 1)}
        self.assertFalse(
            has_line_of_sight((0, 1), (4, 1), transparent.__contains__)
        )

    def test_supercover_blocks_diagonal_corner_leaks(self) -> None:
        cells = supercover_line((0, 0), (2, 2))
        self.assertIn((1, 0), cells)
        self.assertIn((0, 1), cells)

        transparent = {(0, 0), (0, 1), (1, 1), (1, 2), (2, 1), (2, 2)}
        self.assertFalse(
            has_line_of_sight((0, 0), (2, 2), transparent.__contains__)
        )


if __name__ == "__main__":
    unittest.main()

