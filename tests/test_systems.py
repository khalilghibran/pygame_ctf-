"""Tests for terminal hacking, CCTV, and EMP expansion systems."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from player import Player
from systems import CCTV, EMPCharge, HackingPuzzle, HackingState, Terminal


class HackingTests(unittest.TestCase):
    def test_correct_sequence_succeeds(self) -> None:
        puzzle = HackingPuzzle(("1", "4", "2", "3"), reveal_duration=0.1)
        puzzle.update(0.1)
        self.assertEqual(puzzle.state, HackingState.INPUT)
        for symbol in "1423":
            self.assertTrue(puzzle.enter_symbol(symbol))
        self.assertTrue(puzzle.submit())
        self.assertTrue(puzzle.succeeded)

    def test_failed_attempt_reveals_again_then_locks(self) -> None:
        puzzle = HackingPuzzle(("1", "2"), reveal_duration=0.0, max_attempts=2)
        puzzle.update(0.0)
        puzzle.submit(("2", "1"))
        self.assertFalse(puzzle.submit())
        self.assertEqual(puzzle.state, HackingState.REVEAL)
        puzzle.update(0.0)
        puzzle.submit(("2", "1"))
        self.assertFalse(puzzle.submit())
        self.assertTrue(puzzle.failed)


class WorldSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_terminal_requires_key_and_marks_hacked(self) -> None:
        player = Player((24, 24))
        terminal = Terminal((48, 24))
        self.assertIsNone(terminal.begin_hack(player, sequence=(1, 2, 3, 4)))
        player.give_keycard()
        self.assertIsNotNone(terminal.begin_hack(player, sequence=(1, 2, 3, 4)))
        terminal.mark_hacked()
        self.assertTrue(terminal.hacked)

    def test_emp_pickup_respects_player_capacity(self) -> None:
        player = Player((24, 24), max_emp_charges=1)
        first = EMPCharge((24, 24))
        second = EMPCharge((24, 24))
        self.assertTrue(first.interact(player))
        self.assertEqual(player.emp_charges, 1)
        self.assertFalse(second.interact(player))
        self.assertTrue(player.use_emp_charge())
        self.assertTrue(second.interact(player))

    def test_camera_fov_detection_and_disable(self) -> None:
        camera = CCTV((0, 0), base_angle=0, range_pixels=100, fov_degrees=60, sweep_degrees=0, sweep_speed=0, detection_seconds=0.2)
        self.assertTrue(camera.can_see((50, 0), lambda *_: True))
        self.assertFalse(camera.can_see((0, 50), lambda *_: True))
        self.assertFalse(camera.update(0.1, (50, 0), lambda *_: True))
        self.assertTrue(camera.update(0.1, (50, 0), lambda *_: True))
        camera.disable(1.0)
        self.assertFalse(camera.can_see((50, 0), lambda *_: True))
        self.assertFalse(camera.update(0.1, (50, 0), lambda *_: True))


if __name__ == "__main__":
    unittest.main()
