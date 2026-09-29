"""Integration tests for the Sector B campaign chapters."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from enemy import EnemyState
from game import Game, Scene
from level import TileMap
from pathfinding import astar


ROOT = Path(__file__).resolve().parents[1]


class SectorBLevelTests(unittest.TestCase):
    def test_chapter_three_layout_and_routes(self) -> None:
        level = TileMap.from_file(ROOT / "levels" / "level_03.txt")

        self.assertEqual(level.dimensions, (24, 10))
        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.exit_position, (22, 1))
        self.assertEqual(level.keycard_positions, ((10, 7),))
        self.assertEqual(level.terminal_positions, ((19, 2), (20, 7)))
        self.assertEqual(level.door_positions, ((12, 4),))
        self.assertEqual(len(level.enemy_spawns), 2)
        self.assertEqual(len(level.camera_positions), 2)
        self.assertEqual(len(level.hunter_spawns), 1)

        self._assert_mission_routes(level)

    def test_chapter_four_layout_and_routes(self) -> None:
        level = TileMap.from_file(ROOT / "levels" / "level_04.txt")

        self.assertEqual(level.dimensions, (24, 10))
        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.exit_position, (22, 8))
        self.assertEqual(level.keycard_positions, ((6, 7),))
        self.assertEqual(level.terminal_positions, ((19, 2), (13, 6), (20, 7)))
        self.assertEqual(level.door_positions, ((16, 3), (8, 6)))
        self.assertEqual(len(level.enemy_spawns), 3)
        self.assertEqual(len(level.camera_positions), 4)
        self.assertEqual(len(level.emp_positions), 2)
        self.assertEqual(len(level.hunter_spawns), 2)

        self._assert_mission_routes(level)

    def _assert_mission_routes(self, level: TileMap) -> None:
        keycard = level.keycard_positions[0]
        self.assertTrue(astar(level.player_spawn, keycard, level.is_walkable))
        self.assertEqual(astar(level.player_spawn, level.exit_position, level.is_walkable), [])

        opened = set(level.door_positions)
        walkable = lambda position: level.is_walkable(position, opened_doors=opened)
        for terminal in level.terminal_positions:
            self.assertTrue(astar(keycard, terminal, walkable))
            self.assertTrue(astar(terminal, level.exit_position, walkable))


class SectorBGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.game = Game(fullscreen=False)

    def _complete_terminal(self, index: int, sequence: str = "1234") -> None:
        game = self.game
        terminal = game.terminals[index]
        puzzle = terminal.begin_hack(game.player, sequence=sequence)
        self.assertIsNotNone(puzzle)
        puzzle.update(puzzle.reveal_duration)
        game.active_terminal = terminal
        game.hacking_puzzle = puzzle
        game.scene = Scene.HACKING
        for symbol in sequence:
            game._handle_hacking_key(
                pygame.event.Event(
                    pygame.KEYDOWN,
                    key=getattr(pygame, f"K_{symbol}"),
                    unicode=symbol,
                )
            )
        game._handle_hacking_key(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
        )

    def _move_player_to_tile(self, tile: tuple[int, int]) -> None:
        position = self.game._tile_center(tile)
        self.game.player.position.update(position)
        self.game.player.rect.center = tuple(map(round, position))

    def test_chapter_three_requires_both_relays(self) -> None:
        game = self.game
        game._load_level(2)
        game.player.give_keycard()
        game.hunters[0].activate(game.player.position)

        self._complete_terminal(0)

        self.assertFalse(game.terminal_hacked)
        self.assertIn("(1/2)", game.objective)
        self.assertTrue(all(not camera.permanently_disabled for camera in game.cameras))
        self.assertTrue(game.hunters[0].active)
        self._move_player_to_tile((21, 1))
        game._interact()
        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertFalse(game.exit.activated)

        self._complete_terminal(1)

        self.assertTrue(game.terminal_hacked)
        self.assertTrue(all(camera.permanently_disabled for camera in game.cameras))
        self.assertTrue(all(hunter.dormant for hunter in game.hunters))
        self.assertEqual(game.alarm_level, 0)
        self.assertIn("quarantine lift", game.objective)
        game._interact()
        self.assertEqual(game.scene, Scene.WON)
        self.assertTrue(game.exit.activated)

    def test_chapter_four_spawns_full_core_security_and_tracks_seals(self) -> None:
        game = self.game
        game._load_level(3)

        self.assertEqual(len(game.enemies), 3)
        self.assertEqual(len(game.cameras), 4)
        self.assertEqual(len(game.terminals), 3)
        self.assertEqual(len(game.hunters), 2)
        game.player.give_keycard()
        self._complete_terminal(0)
        self.assertIn("(1/3)", game.objective)

    def test_secondary_guard_state_is_visible_in_hud(self) -> None:
        game = self.game
        game._load_level(2)
        self.assertEqual(len(game.enemies), 2)
        game.enemies[1].set_state(EnemyState.CHASE)

        self.assertEqual(game.security_state_name, "CHASE")

    def test_terminal_disconnect_preserves_current_puzzle(self) -> None:
        game = self.game
        game._load_level(2)
        game.player.give_keycard()
        terminal = game.terminals[0]
        first = terminal.begin_hack(game.player, sequence="1234")
        self.assertIsNotNone(first)
        first.update(first.reveal_duration)
        first.enter_symbol("1")

        resumed = terminal.begin_hack(game.player, sequence="4321")

        self.assertIs(resumed, first)
        self.assertEqual(resumed.sequence, ("1", "2", "3", "4"))
        self.assertEqual(resumed.entered, ("1",))


if __name__ == "__main__":
    unittest.main()
