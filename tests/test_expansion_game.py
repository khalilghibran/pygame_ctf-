"""End-to-end tests for the Lab A-2 expansion flow."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import Game, Scene


class ExpansionGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.game = Game()
        self.game._load_level(1)

    def move_player_to_tile(self, tile: tuple[int, int]) -> None:
        position = self.game._tile_center(tile)
        self.game.player.position.update(position)
        self.game.player.rect.center = tuple(map(round, position))

    def test_expansion_world_spawns_every_new_system(self) -> None:
        game = self.game
        self.assertEqual(game.level_index, 1)
        self.assertEqual(game.level.dimensions, (24, 10))
        self.assertEqual(len(game.terminals), 1)
        self.assertEqual(len(game.cameras), 1)
        self.assertEqual(len(game.emp_pickups), 1)
        self.assertEqual(len(game.hunters), 1)
        self.assertTrue(game.hunters[0].dormant)
        self.assertFalse(game.terminal_hacked)

    def test_objective_and_exit_require_key_then_terminal(self) -> None:
        game = self.game
        self.assertIn("blue keycard", game.objective)
        game.player.give_keycard()
        self.assertIn("Hack", game.objective)

        self.move_player_to_tile((21, 1))
        game._interact()
        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertFalse(game.exit.activated)

        game.terminals[0].mark_hacked()
        self.assertIn("exit", game.objective)
        game._interact()
        self.assertEqual(game.scene, Scene.WON)
        self.assertTrue(game.exit.activated)

    def test_successful_hack_disables_camera_network(self) -> None:
        game = self.game
        game.player.give_keycard()
        terminal = game.terminals[0]
        puzzle = terminal.begin_hack(game.player, sequence=("3", "1", "4", "2"))
        self.assertIsNotNone(puzzle)
        game.active_terminal = terminal
        game.hacking_puzzle = puzzle
        game.scene = Scene.HACKING
        puzzle.update(puzzle.reveal_duration)

        for symbol in "3142":
            event = pygame.event.Event(
                pygame.KEYDOWN, key=getattr(pygame, f"K_{symbol}"), unicode=symbol
            )
            game._handle_hacking_key(event)
        game._handle_hacking_key(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")
        )

        self.assertEqual(game.scene, Scene.PLAYING)
        self.assertTrue(terminal.hacked)
        self.assertTrue(game.cameras[0].permanently_disabled)
        self.assertEqual(game.alarm_level, 0)

    def test_alarm_level_two_releases_hunter_x(self) -> None:
        game = self.game
        hunter = game.hunters[0]
        game._raise_alarm(2, game.player.position, "TEST ALARM")

        self.assertEqual(game.alarm_level, 2)
        self.assertTrue(hunter.active)
        self.assertFalse(hunter.dormant)
        self.assertIsNotNone(hunter.last_seen_position)

    def test_cctv_detection_raises_network_alarm(self) -> None:
        game = self.game
        self.move_player_to_tile((20, 5))
        camera = game.cameras[0]
        offset = game.player.position - camera.position
        camera.angle = pygame.Vector2(1, 0).angle_to(offset)
        camera.base_angle = camera.angle
        camera.sweep_degrees = 0.0
        camera.sweep_speed = 0.0
        camera.detection_seconds = 0.05

        game._update(0.05)

        self.assertEqual(game.alarm_level, 1)
        self.assertEqual(game.security_events, 1)
        self.assertIsNotNone(game.enemy.last_seen_position)

    def test_emp_disables_nearby_camera_and_hunter(self) -> None:
        game = self.game
        self.move_player_to_tile((15, 4))
        hunter = game.hunters[0]
        hunter.activate(game.player.position)
        game.player.add_emp_charge()

        self.assertTrue(game._activate_emp())
        self.assertEqual(game.player.emp_charges, 0)
        self.assertTrue(game.cameras[0].disabled)
        self.assertTrue(hunter.disabled)
        self.assertGreater(game.emp_effect_remaining, 0.0)

    def test_level_two_and_hacking_screens_render_headlessly(self) -> None:
        game = self.game
        game._draw()
        game.player.give_keycard()
        game.active_terminal = game.terminals[0]
        game.hacking_puzzle = game.active_terminal.begin_hack(
            game.player, sequence=(1, 2, 3, 4)
        )
        game.scene = Scene.HACKING
        game._draw()
        self.assertEqual(game.screen.get_size(), (1280, 720))


if __name__ == "__main__":
    unittest.main()
