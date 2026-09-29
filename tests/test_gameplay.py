"""Headless integration tests for gameplay models and orchestration."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import settings
from assets import SpriteLibrary
from enemy import EnemyState
from game import Game, Scene


class GameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.game = Game()

    def move_player_to_tile(self, tile: tuple[int, int]) -> None:
        position = self.game._tile_center(tile)
        self.game.player.position.update(position)
        self.game.player.rect.center = tuple(map(round, position))

    def test_world_matches_handoff_level(self) -> None:
        game = self.game
        self.assertEqual(game.level.dimensions, (24, 10))
        self.assertEqual(game.level.player_spawn, (1, 1))
        self.assertEqual(game.enemy.tile, (6, 5))
        self.assertEqual(game.level.battery_positions, ((17, 1),))
        self.assertEqual(game.level.door_positions, ((12, 3),))
        self.assertEqual(game.level.keycard_positions, ((15, 7),))
        self.assertEqual(game.level.exit_position, (20, 8))
        self.assertEqual(game.scene, Scene.MENU)

    def test_exit_denies_then_accepts_blue_keycard(self) -> None:
        game = self.game
        game.scene = Scene.PLAYING
        self.move_player_to_tile((19, 8))

        game._interact()
        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertFalse(game.exit.activated)

        game.player.give_keycard("blue")
        game._interact()
        self.assertEqual(game.scene, Scene.WON)
        self.assertTrue(game.exit.activated)

    def test_access_door_blocks_sight_until_opened(self) -> None:
        game = self.game
        above = game._tile_center((12, 2))
        below = game._tile_center((12, 4))

        self.assertFalse(game._line_of_sight(above, below))
        self.assertTrue(game.doors[0].blocks)
        self.assertFalse(game.doors[0].interact(game.player))

        game.player.give_keycard("blue")
        self.assertTrue(game.doors[0].interact(game.player))
        self.assertFalse(game.doors[0].blocks)
        self.assertTrue(game._line_of_sight(above, below))

    def test_battery_drain_restore_and_full_pickup_rule(self) -> None:
        player = self.game.player
        battery = self.game.batteries[0]

        self.assertTrue(player.drain_battery(1_000.0))
        self.assertEqual(player.battery, 0.0)
        self.assertEqual(player.restore_battery(500.0), settings.BATTERY_MAX)
        self.assertEqual(player.battery, settings.BATTERY_MAX)
        self.assertFalse(battery.interact(player))
        self.assertTrue(battery.active)

        player.battery = 40.0
        self.assertTrue(battery.interact(player))
        self.assertFalse(battery.active)
        self.assertEqual(player.battery, 40.0 + settings.BATTERY_PICKUP_AMOUNT)

    def test_security_state_cycle_is_reachable(self) -> None:
        game = self.game
        bot = game.enemy
        self.move_player_to_tile((6, 4))
        bot.update(
            1 / 60,
            game.player,
            game.blockers,
            tile_map=game.level,
            opened_doors=game.opened_door_tiles,
            los_test=game._line_of_sight,
        )
        self.assertEqual(bot.state, EnemyState.CHASE)

        self.move_player_to_tile((1, 1))
        bot.update(
            1 / 60,
            game.player,
            game.blockers,
            tile_map=game.level,
            opened_doors=game.opened_door_tiles,
            los_test=game._line_of_sight,
        )
        self.assertEqual(bot.state, EnemyState.SEARCH)

        for _ in range(round((bot.search_duration + 0.2) * 60)):
            bot.update(
                1 / 60,
                game.player,
                game.blockers,
                tile_map=game.level,
                opened_doors=game.opened_door_tiles,
                los_test=game._line_of_sight,
            )
        self.assertIn(bot.state, (EnemyState.RETURN, EnemyState.PATROL))

    def test_reset_restores_all_mutable_mission_state(self) -> None:
        game = self.game
        game.player.give_keycard()
        game.player.battery = 12.0
        game.keycards[0].interact(game.player)
        game.batteries[0].active = False
        game.doors[0].open()
        game.enemy.set_state(EnemyState.CHASE)
        game.elapsed = 42.0

        game._reset_world()

        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertFalse(game.player.has_keycard())
        self.assertEqual(game.player.battery, settings.BATTERY_MAX)
        self.assertTrue(game.keycards[0].active)
        self.assertTrue(game.batteries[0].active)
        self.assertTrue(game.doors[0].blocks)
        self.assertEqual(game.enemy.state, EnemyState.PATROL)
        self.assertEqual(game.elapsed, 0.0)

    def test_headless_render_and_update_smoke(self) -> None:
        game = self.game
        game.scene = Scene.PLAYING
        for _ in range(10):
            game._update(1 / 60)
        game._draw()

        self.assertEqual(game.screen.get_size(), settings.SCREEN_SIZE)
        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertLess(game.player.battery, settings.BATTERY_MAX)
        self.assertEqual(game.enemy.state, EnemyState.PATROL)

    def test_asset_fallback_api_covers_runtime_art(self) -> None:
        assets = SpriteLibrary(tile_size=settings.TILE_SIZE)
        names = (
            "player_idle_down.png",
            "security_walk_left_1.png",
            "floor_clean.png",
            "wall_top.png",
            "door_locked.png",
            "exit_door.png",
            "keycard_blue.png",
            "battery_pack.png",
            "emp_charge.png",
            "terminal.png",
            "cctv_down.png",
            "hunter_idle.png",
            "warden_prime.png",
        )
        surfaces = [assets.get(name) for name in names]
        surfaces.extend(
            (
                assets.detection_cone(),
                assets.glow(settings.PLAYER_CYAN, 24),
                assets.ui_panel((120, 40)),
            )
        )
        self.assertTrue(all(surface and surface.get_width() for surface in surfaces))
        self.assertGreaterEqual(len(assets.manifest_names), 70)


if __name__ == "__main__":
    unittest.main()
