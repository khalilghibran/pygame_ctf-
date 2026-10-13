"""Regressions for the gentler late-campaign Explorer checkpoints."""

from __future__ import annotations

import math
import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import settings
from difficulty import EXPLORER
from game import Game, Scene
from level import TileMap
from pathfinding import astar


ROOT = Path(__file__).resolve().parents[1]


class LateChapterMapTests(unittest.TestCase):
    def test_early_batteries_and_mission_routes(self) -> None:
        expectations = {
            3: ((5, 7), 2, 2, 2, 1),
            4: ((3, 8), 3, 3, 3, 2),
            5: ((2, 7), 3, 2, 3, 0),
        }
        for chapter, (early_battery, batteries, guards, terminals, hunters) in expectations.items():
            with self.subTest(chapter=chapter):
                level = TileMap.from_file(ROOT / "levels" / f"level_{chapter:02}.txt")
                self.assertEqual(level.dimensions, (24, 10))
                self.assertEqual(len(level.battery_positions), batteries)
                self.assertEqual(len(level.enemy_spawns), guards)
                self.assertEqual(len(level.terminal_positions), terminals)
                self.assertEqual(len(level.hunter_spawns), hunters)
                self.assertIn(early_battery, level.battery_positions)
                self.assertTrue(astar(level.player_spawn, early_battery, level.is_walkable))

                key = level.keycard_positions[0]
                self.assertTrue(astar(level.player_spawn, key, level.is_walkable))
                self.assertFalse(astar(level.player_spawn, level.exit_position, level.is_walkable))
                opened = set(level.door_positions)
                walkable = lambda tile: level.is_walkable(tile, opened_doors=opened)
                for terminal in level.terminal_positions:
                    self.assertTrue(astar(key, terminal, walkable))
                    self.assertTrue(astar(terminal, level.exit_position, walkable))

    def test_initial_guards_start_outside_explorer_detection_range(self) -> None:
        for chapter in (3, 4, 5):
            with self.subTest(chapter=chapter):
                level = TileMap.from_file(ROOT / "levels" / f"level_{chapter:02}.txt")
                spawn = level.player_spawn
                for guard in level.enemy_spawns:
                    distance_in_tiles = math.dist(spawn, guard)
                    self.assertGreater(
                        distance_in_tiles * settings.TILE_SIZE,
                        EXPLORER.enemy_detection_range,
                    )


class LateChapterExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    @staticmethod
    def _complete_terminal(game: Game, index: int) -> None:
        sequence = "123" if game.difficulty.name == "EXPLORER" else "1234"
        terminal = game.terminals[index]
        puzzle = terminal.begin_hack(game.player, sequence=sequence)
        assert puzzle is not None
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
        assert terminal.hacked
        assert game.scene is Scene.PLAYING

    def test_hunters_wait_for_level_three_alarm_only_in_late_explorer(self) -> None:
        for mode in ("explorer", "classic"):
            for level_index in (2, 3):
                with self.subTest(mode=mode, chapter=level_index + 1):
                    game = Game(fullscreen=False, difficulty=mode)
                    game._load_level(level_index)
                    self.assertTrue(game.hunters)
                    game._raise_alarm(2, game.player.position, "TEST TRACE")
                    self.assertEqual(
                        all(hunter.active for hunter in game.hunters),
                        mode == "classic",
                    )
                    game._raise_alarm(1, game.player.position, "TEST TRACE")
                    self.assertTrue(all(hunter.active for hunter in game.hunters))

    def test_hacks_reward_explorer_but_leave_classic_rules_intact(self) -> None:
        for mode in ("explorer", "classic"):
            for level_index in (2, 3, 4):
                with self.subTest(mode=mode, chapter=level_index + 1):
                    game = Game(fullscreen=False, difficulty=mode)
                    game._load_level(level_index)
                    game.player.give_keycard()
                    game.player.battery = 40.0
                    game.player.emp_charges = 0
                    game.alarm_level = 3
                    for hunter in game.hunters:
                        hunter.activate(game.player.position)

                    self._complete_terminal(game, 0)

                    self.assertFalse(game.terminal_hacked)
                    self.assertFalse(any(camera.permanently_disabled for camera in game.cameras))
                    if mode == "explorer":
                        self.assertEqual(game.player.battery, 55.0)
                        self.assertEqual(game.player.emp_charges, 1)
                        self.assertEqual(game.alarm_level, 0)
                        self.assertTrue(all(hunter.dormant for hunter in game.hunters))
                    else:
                        self.assertEqual(game.player.battery, 40.0)
                        self.assertEqual(game.player.emp_charges, 0)
                        self.assertEqual(game.alarm_level, 2)
                        self.assertTrue(all(hunter.active for hunter in game.hunters))

                    for index in range(1, len(game.terminals) - 1):
                        self._complete_terminal(game, index)

                    game.player.battery = 90.0
                    game.player.emp_charges = 0
                    self._complete_terminal(game, len(game.terminals) - 1)

                    self.assertTrue(game.terminal_hacked)
                    self.assertEqual(game.player.battery, 100.0 if mode == "explorer" else 90.0)
                    self.assertEqual(game.alarm_level, 0)
                    self.assertTrue(all(camera.permanently_disabled for camera in game.cameras))
                    self.assertTrue(all(hunter.dormant for hunter in game.hunters))
                    if level_index == 4:
                        self.assertEqual(game.player.emp_charges, 3)

                    # Once the network is down, later traces must not revive Hunters.
                    game._raise_alarm(3, game.player.position, "TEST TRACE")
                    self.assertTrue(all(hunter.dormant for hunter in game.hunters))

    def test_hacked_terminal_is_not_an_interaction_obstacle(self) -> None:
        game = Game(fullscreen=False, difficulty="explorer")
        game._load_level(2)
        terminal = game.terminals[0]
        terminal.mark_hacked()
        game.player.position.update(terminal.position)
        game.player.rect.center = tuple(map(round, terminal.position))

        self.assertIsNot(game._interaction_target(), terminal)


if __name__ == "__main__":
    unittest.main()
