"""Headless tests for the optional Hunter-X expansion enemy."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from enemy import EnemyState, SecurityBot
from hunter import HunterX


def player_at(center: tuple[float, float]) -> SimpleNamespace:
    rect = pygame.Rect(0, 0, 24, 24)
    rect.center = tuple(map(round, center))
    return SimpleNamespace(position=pygame.Vector2(center), rect=rect)


class HunterXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_defaults_are_dormant_stronger_and_wider(self) -> None:
        standard = SecurityBot((24, 24), waypoints=[(24, 24)])
        hunter = HunterX((24, 24), waypoints=[(24, 24)])

        self.assertFalse(hunter.active)
        self.assertEqual(hunter.state_name, "DORMANT")
        self.assertGreater(hunter.patrol_speed, standard.patrol_speed)
        self.assertGreater(hunter.chase_speed, standard.chase_speed)
        self.assertGreater(hunter.detection_range, standard.detection_range)
        self.assertGreater(hunter.rect.width, standard.rect.width)

    def test_dormant_hunter_does_not_detect_move_or_catch(self) -> None:
        hunter = HunterX((24, 24), waypoints=[(24, 24), (120, 24)])
        player = player_at((24, 24))

        hunter.update(1.0, player)

        self.assertEqual(hunter.position, pygame.Vector2(24, 24))
        self.assertEqual(hunter.velocity, pygame.Vector2())
        self.assertFalse(hunter.sees_player(player))
        self.assertFalse(hunter.touching_player(player))
        self.assertEqual(hunter.state, EnemyState.PATROL)

    def test_activate_accepts_last_seen_and_uses_security_state_machine(self) -> None:
        hunter = HunterX((24, 24), waypoints=[(24, 24), (120, 24)])
        player = player_at((96, 24))

        self.assertTrue(hunter.activate(player))
        self.assertFalse(hunter.activate(player.position))
        self.assertEqual(hunter.state, EnemyState.CHASE)
        self.assertEqual(hunter.last_seen_position, player.position)
        hunter.update(0.1, player)

        self.assertGreater(hunter.position.x, 24)
        self.assertEqual(hunter.state_name, "CHASE")
        self.assertEqual(hunter.facing, "right")

    def test_emp_stun_suppresses_detection_movement_and_capture(self) -> None:
        hunter = HunterX((24, 24), active=True, waypoints=[(24, 24), (120, 24)])
        overlapping_player = player_at((24, 24))

        self.assertTrue(hunter.disable(0.5))
        hunter.update(0.2, overlapping_player)

        self.assertAlmostEqual(hunter.disabled_remaining, 0.3)
        self.assertEqual(hunter.state_name, "DISABLED")
        self.assertEqual(hunter.position, pygame.Vector2(24, 24))
        self.assertFalse(hunter.sees_player(overlapping_player))
        self.assertFalse(hunter.touching_player(overlapping_player))

        # A weaker repeated stun never shortens the existing effect.
        hunter.disable(0.1)
        self.assertAlmostEqual(hunter.disabled_remaining, 0.3)
        hunter.update(0.3, overlapping_player)
        self.assertFalse(hunter.is_disabled)
        self.assertTrue(hunter.touching_player(overlapping_player))

    def test_reset_restores_configured_activity_and_clears_stun(self) -> None:
        dormant = HunterX((24, 24))
        dormant.activate((96, 24))
        dormant.disable(2.0)
        dormant.position.update(60, 60)
        dormant.rect.center = (60, 60)
        dormant.reset()

        self.assertFalse(dormant.active)
        self.assertFalse(dormant.is_disabled)
        self.assertEqual(dormant.position, pygame.Vector2(24, 24))
        self.assertEqual(dormant.state_name, "DORMANT")

        configured_active = HunterX((24, 24), active=True)
        configured_active.deactivate()
        configured_active.reset()
        self.assertTrue(configured_active.active)
        self.assertEqual(configured_active.state, EnemyState.PATROL)

    def test_from_tile_preserves_bot_compatibility(self) -> None:
        hunter = HunterX.from_tile(
            (2, 3),
            waypoints=[(2, 3), (4, 3)],
            tile_size=48,
            active=True,
        )

        self.assertEqual(hunter.tile, (2, 3))
        self.assertEqual(hunter.rect.center, (120, 168))
        self.assertEqual(hunter.waypoints[1], pygame.Vector2(216, 168))


if __name__ == "__main__":
    unittest.main()
