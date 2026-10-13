"""Headless regressions for the player-selectable accessibility profiles."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import settings
from difficulty import CLASSIC, EXPLORER
from game import Game, Scene


class AccessibilityProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    @staticmethod
    def _move_player_to(game: Game, tile: tuple[int, int]) -> None:
        position = game._tile_center(tile)
        game.player.position.update(position)
        game.player.rect.center = tuple(map(round, position))

    @staticmethod
    def _press(game: Game, key: int) -> None:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        game._handle_events()

    def test_explorer_is_default_and_tab_selects_classic(self) -> None:
        game = Game(fullscreen=False)
        pygame.event.clear()
        self.assertEqual(game.scene, Scene.MENU)
        self.assertIs(game.difficulty, EXPLORER)

        self._press(game, pygame.K_TAB)
        self.assertEqual(game.scene, Scene.MENU)
        self.assertIs(game.difficulty, CLASSIC)
        self.assertEqual(game.player.speed, CLASSIC.player_speed)

        self._press(game, pygame.K_RETURN)
        self.assertEqual(game.scene, Scene.BRIEFING)
        self.assertIs(game.difficulty, CLASSIC)

        game.scene = Scene.MENU
        self._press(game, pygame.K_TAB)
        self.assertIs(game.difficulty, EXPLORER)

    def test_player_can_change_mode_after_pausing_a_chapter(self) -> None:
        game = Game(fullscreen=False, difficulty="classic")
        pygame.event.clear()
        game._load_level(3)
        self._press(game, pygame.K_h)
        self.assertEqual(game.scene, Scene.PAUSED)
        self._press(game, pygame.K_m)
        self.assertEqual(game.scene, Scene.MENU)
        self._press(game, pygame.K_TAB)
        self.assertIs(game.difficulty, EXPLORER)
        self._press(game, pygame.K_4)
        self.assertEqual(game.level_index, 3)
        self.assertEqual(game.scene, Scene.BRIEFING)
        self.assertEqual(game.player.speed, EXPLORER.player_speed)

    def test_profile_changes_movement_battery_and_camera_timing(self) -> None:
        for mode, profile in (("explorer", EXPLORER), ("classic", CLASSIC)):
            with self.subTest(mode=mode):
                game = Game(fullscreen=False, difficulty=mode)
                self.assertEqual(game.player.speed, profile.player_speed)
                self.assertEqual(game.enemy.patrol_speed, profile.enemy_patrol_speed)
                self.assertEqual(game.enemy.chase_speed, profile.enemy_chase_speed)

                game.scene = Scene.PLAYING
                battery_before = game.player.battery
                game._update(0.25)
                self.assertAlmostEqual(
                    battery_before - game.player.battery,
                    profile.battery_drain * 0.25,
                    places=4,
                )

                game._load_level(1)
                self.assertTrue(game.cameras)
                self.assertTrue(
                    all(
                        camera.detection_seconds == profile.cctv_detection_seconds
                        for camera in game.cameras
                    )
                )

        self.assertLess(EXPLORER.battery_drain, CLASSIC.battery_drain)
        self.assertGreater(
            EXPLORER.cctv_detection_seconds, CLASSIC.cctv_detection_seconds
        )

    def test_explorer_hack_has_three_symbols_and_longer_reveal(self) -> None:
        puzzles = {}
        for mode in ("explorer", "classic"):
            game = Game(fullscreen=False, difficulty=mode)
            game._load_level(1)
            game.player.give_keycard()
            self._move_player_to(game, game.level.terminal_positions[0])
            game._interact()

            self.assertEqual(game.scene, Scene.HACKING)
            self.assertIsNotNone(game.hacking_puzzle)
            puzzles[mode] = game.hacking_puzzle

        self.assertEqual(len(puzzles["explorer"].sequence), 3)
        self.assertEqual(len(puzzles["classic"].sequence), 4)
        self.assertGreater(
            puzzles["explorer"].reveal_duration,
            puzzles["classic"].reveal_duration,
        )
        self.assertGreater(
            puzzles["explorer"].attempts_remaining,
            puzzles["classic"].attempts_remaining,
        )

    def test_explorer_walks_over_keycard_to_collect_it(self) -> None:
        for mode, automatically_collected in (("explorer", True), ("classic", False)):
            with self.subTest(mode=mode):
                game = Game(fullscreen=False, difficulty=mode)
                self._move_player_to(game, game.level.keycard_positions[0])
                game.scene = Scene.PLAYING
                game._update(1 / 60)
                self.assertEqual(game.player.has_keycard(), automatically_collected)
                self.assertEqual(game.keycards[0].active, not automatically_collected)

    def test_explorer_saves_auto_battery_pickup_until_it_is_useful(self) -> None:
        game = Game(fullscreen=False, difficulty="explorer")
        self._move_player_to(game, game.level.battery_positions[0])
        game.scene = Scene.PLAYING

        game._update(1 / 60)
        self.assertTrue(game.batteries[0].active)

        game.player.battery = 60.0
        game._update(1 / 60)
        self.assertFalse(game.batteries[0].active)
        self.assertGreater(game.player.battery, 99.0)

    def test_explorer_contact_grace_vs_classic_capture(self) -> None:
        explorer = Game(fullscreen=False, difficulty="explorer")
        explorer.scene = Scene.PLAYING
        battery_before = explorer.player.battery

        self.assertFalse(explorer._handle_security_contact(explorer.enemy))
        self.assertEqual(explorer.scene, Scene.PLAYING)
        self.assertAlmostEqual(
            explorer.player.battery,
            battery_before - EXPLORER.contact_battery_penalty,
        )
        self.assertGreater(explorer.contact_grace_remaining, 0)
        battery_after_first_contact = explorer.player.battery
        self.assertFalse(explorer._handle_security_contact(explorer.enemy))
        self.assertEqual(explorer.player.battery, battery_after_first_contact)

        classic = Game(fullscreen=False, difficulty="classic")
        classic.scene = Scene.PLAYING
        self.assertTrue(classic._handle_security_contact(classic.enemy))
        self.assertEqual(classic.scene, Scene.CAUGHT)

    def test_both_modes_draw_title_and_boss_level_headlessly(self) -> None:
        for mode in ("explorer", "classic"):
            with self.subTest(mode=mode):
                game = Game(fullscreen=False, difficulty=mode)
                game._draw()
                self.assertEqual(game.screen.get_size(), settings.SCREEN_SIZE)
                game._load_level(4)
                game._draw()
                self.assertEqual(game.scene, Scene.PLAYING)


if __name__ == "__main__":
    unittest.main()
