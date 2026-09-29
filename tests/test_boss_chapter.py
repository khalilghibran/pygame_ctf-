"""Unit and integration coverage for the Chapter V boss encounter."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import settings
from boss import BossHit, WardenPrime
from game import Game, Scene
from level import TileMap
from pathfinding import astar


ROOT = Path(__file__).resolve().parents[1]


class WardenPrimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.boss = WardenPrime(
            (120, 120),
            ((120, 120), (220, 120)),
            tile_size=48,
            size=52,
            hit_cooldown=1.0,
            stun_seconds=0.5,
        )

    def test_shielded_emp_stuns_without_dealing_damage(self) -> None:
        result = self.boss.receive_emp(shield_down=False)

        self.assertEqual(result, BossHit.SHIELDED)
        self.assertEqual(self.boss.health, self.boss.max_health)
        self.assertTrue(self.boss.disabled)

    def test_three_exposed_hits_defeat_boss_with_cooldown(self) -> None:
        original_chase_speed = self.boss.chase_speed
        self.assertEqual(self.boss.receive_emp(shield_down=True), BossHit.DAMAGED)
        self.assertEqual(self.boss.health, 2)
        self.assertGreater(self.boss.chase_speed, original_chase_speed)
        self.assertEqual(self.boss.receive_emp(shield_down=True), BossHit.COOLDOWN)
        self.assertEqual(self.boss.health, 2)

        self.boss.damage_cooldown_remaining = 0.0
        self.assertEqual(self.boss.receive_emp(shield_down=True), BossHit.DAMAGED)
        self.boss.damage_cooldown_remaining = 0.0
        self.assertEqual(self.boss.receive_emp(shield_down=True), BossHit.DEFEATED)
        self.assertTrue(self.boss.defeated)
        self.assertEqual(self.boss.health, 0)

    def test_reset_restores_health_and_phase_tuning(self) -> None:
        patrol_speed = self.boss.patrol_speed
        chase_speed = self.boss.chase_speed
        self.boss.receive_emp(shield_down=True)
        self.boss.reset()

        self.assertEqual(self.boss.health, self.boss.max_health)
        self.assertFalse(self.boss.defeated)
        self.assertEqual(self.boss.patrol_speed, patrol_speed)
        self.assertEqual(self.boss.chase_speed, chase_speed)


class BossChapterLevelTests(unittest.TestCase):
    def test_boss_arena_layout_and_routes(self) -> None:
        level = TileMap.from_file(ROOT / "levels" / "level_05.txt")

        self.assertEqual(level.dimensions, (24, 10))
        self.assertEqual(level.player_spawn, (1, 1))
        self.assertEqual(level.exit_position, (22, 8))
        self.assertEqual(level.keycard_positions, ((6, 7),))
        self.assertEqual(level.terminal_positions, ((11, 2), (20, 2), (14, 7)))
        self.assertEqual(level.boss_spawns, ((17, 4),))
        self.assertEqual(len(level.emp_positions), 3)
        self.assertEqual(len(level.enemy_spawns), 2)
        self.assertEqual(len(level.camera_positions), 2)

        keycard = level.keycard_positions[0]
        self.assertTrue(astar(level.player_spawn, keycard, level.is_walkable))
        self.assertEqual(astar(level.player_spawn, level.exit_position, level.is_walkable), [])
        opened = set(level.door_positions)
        walkable = lambda position: level.is_walkable(position, opened_doors=opened)
        for destination in (
            *level.terminal_positions,
            *level.boss_spawns,
            level.exit_position,
        ):
            self.assertTrue(astar(keycard, destination, walkable))


class BossChapterGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.game = Game(fullscreen=False)
        self.game._load_level(4)

    def _move_player_to(self, position: pygame.Vector2) -> None:
        self.game.player.position.update(position)
        self.game.player.rect.center = tuple(map(round, position))

    def test_boss_world_spawns_and_renders(self) -> None:
        game = self.game
        self.assertIsNotNone(game.boss)
        self.assertEqual(len(game.bosses), 1)
        self.assertFalse(game.boss_defeated)
        self.assertFalse(game.exit_ready)
        self.assertEqual(game.boss.health, settings.BOSS_MAX_HEALTH)
        game._draw()
        self.assertEqual(game.screen.get_size(), settings.SCREEN_SIZE)

    def test_final_anchor_exposes_boss_and_refills_emp(self) -> None:
        game = self.game
        game.player.give_keycard()
        game.player.emp_charges = 0
        for terminal in game.terminals[:-1]:
            terminal.mark_hacked()
        terminal = game.terminals[-1]
        puzzle = terminal.begin_hack(game.player, sequence="1234")
        self.assertIsNotNone(puzzle)
        puzzle.update(puzzle.reveal_duration)
        game.active_terminal = terminal
        game.hacking_puzzle = puzzle
        game.scene = Scene.HACKING
        for symbol in "1234":
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

        self.assertTrue(game.terminal_hacked)
        self.assertEqual(game.player.emp_charges, 3)
        self.assertEqual(game.boss.state_name, "CHASE")
        self.assertTrue(all(camera.permanently_disabled for camera in game.cameras))
        self.assertIn("3/3", game.objective)

    def test_emp_range_cooldown_damage_and_exit_gate(self) -> None:
        game = self.game
        game.player.give_keycard()
        for terminal in game.terminals:
            terminal.mark_hacked()
        game.player.add_emp_charge(3)

        exit_neighbor = game._tile_center((21, 8))
        self._move_player_to(exit_neighbor)
        game._interact()
        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertFalse(game.exit.activated)

        charges = game.player.emp_charges
        self.assertFalse(game._activate_emp())
        self.assertEqual(game.player.emp_charges, charges)

        self._move_player_to(game.boss.position)
        self.assertTrue(game._activate_emp())
        self.assertEqual(game.boss.health, 2)
        charges = game.player.emp_charges
        self.assertFalse(game._activate_emp())
        self.assertEqual(game.player.emp_charges, charges)

        for expected_health in (1, 0):
            game.boss.damage_cooldown_remaining = 0.0
            self.assertTrue(game._activate_emp())
            self.assertEqual(game.boss.health, expected_health)

        self.assertTrue(game.boss_defeated)
        self.assertTrue(game.exit_ready)
        self._move_player_to(exit_neighbor)
        game._interact()
        self.assertEqual(game.scene, Scene.WON)


if __name__ == "__main__":
    unittest.main()
