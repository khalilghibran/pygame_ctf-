"""Expansion-level parsing and route tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from level import TileMap
from pathfinding import astar


ROOT = Path(__file__).resolve().parents[1]


class ExpansionLevelTests(unittest.TestCase):
    def test_level_02_markers_and_dimensions(self) -> None:
        level = TileMap.from_file(ROOT / "levels" / "level_02.txt")

        self.assertEqual(level.dimensions, (24, 10))
        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.exit_position, (22, 1))
        self.assertEqual(level.camera_positions, ((18, 1),))
        self.assertEqual(level.emp_positions, ((6, 4),))
        self.assertEqual(level.terminal_positions, ((19, 5),))
        self.assertEqual(level.keycard_positions, ((8, 4),))
        self.assertEqual(level.door_positions, ((12, 4),))
        self.assertEqual(level.hunter_spawns, ((15, 6),))
        self.assertEqual(level.battery_positions, ((5, 7),))
        self.assertEqual(level.enemy_spawns, ((5, 8),))
        for position in (
            *level.camera_positions,
            *level.emp_positions,
            *level.terminal_positions,
            *level.hunter_spawns,
        ):
            self.assertTrue(level.is_walkable(position))

    def test_level_01_remains_unchanged(self) -> None:
        level = TileMap.from_file(ROOT / "levels" / "level_01.txt")

        self.assertEqual(level.dimensions, (24, 10))
        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.battery_positions, ((17, 1),))
        self.assertEqual(level.door_positions, ((12, 3),))
        self.assertEqual(level.enemy_spawns, ((6, 5),))
        self.assertEqual(level.keycard_positions, ((15, 7),))
        self.assertEqual(level.exit_position, (20, 8))
        self.assertEqual(level.terminal_positions, ())
        self.assertEqual(level.camera_positions, ())
        self.assertEqual(level.emp_positions, ())
        self.assertEqual(level.hunter_spawns, ())

    def test_level_02_has_intended_key_door_terminal_route(self) -> None:
        level = TileMap.from_file(ROOT / "levels" / "level_02.txt")
        keycard = level.keycard_positions[0]
        terminal = level.terminal_positions[0]

        self.assertEqual(astar(level.player_spawn, level.exit_position, level.is_walkable), [])
        self.assertTrue(astar(level.player_spawn, keycard, level.is_walkable))

        opened = set(level.door_positions)
        walkable = lambda position: level.is_walkable(position, opened_doors=opened)
        key_to_terminal = astar(keycard, terminal, walkable)
        terminal_to_exit = astar(terminal, level.exit_position, walkable)
        self.assertTrue(key_to_terminal)
        self.assertTrue(terminal_to_exit)
        self.assertIn(level.door_positions[0], key_to_terminal)


if __name__ == "__main__":
    unittest.main()
