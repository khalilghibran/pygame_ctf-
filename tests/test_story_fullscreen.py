"""Campaign story progression and fullscreen regression tests."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import settings
from game import Game, Scene
from story import MISSION_STORIES


class StoryAndFullscreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def setUp(self) -> None:
        self.game = Game(fullscreen=False)
        pygame.event.clear()

    def press(self, key: int, *, unicode: str = "", mod: int = 0) -> None:
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=key,
                unicode=unicode,
                mod=mod,
            )
        )
        self.game._handle_events()

    def test_every_level_has_complete_story_data(self) -> None:
        self.assertEqual(len(MISSION_STORIES), 5)
        for story in MISSION_STORIES:
            self.assertTrue(story.chapter)
            self.assertTrue(story.title)
            self.assertTrue(story.story_lines)
            self.assertTrue(story.mission_lines)
            self.assertTrue(story.key_objective)
            self.assertTrue(story.exit_objective)
            self.assertTrue(story.network_clear_message)
            self.assertTrue(story.clear_lines)

    def test_menu_selection_shows_matching_briefing_before_play(self) -> None:
        self.press(pygame.K_RETURN, unicode="\r")
        self.assertEqual(self.game.scene, Scene.BRIEFING)
        self.assertEqual(self.game.level_index, 0)

        self.press(pygame.K_SPACE, unicode=" ")
        self.assertEqual(self.game.scene, Scene.PLAYING)
        self.assertIn("WAKE PROTOCOL", self.game.ui.toast.text)

        self.game.scene = Scene.MENU
        self.press(pygame.K_2, unicode="2")
        self.assertEqual(self.game.scene, Scene.BRIEFING)
        self.assertEqual(self.game.level_index, 1)

        self.game.scene = Scene.MENU
        self.press(pygame.K_3, unicode="3")
        self.assertEqual(self.game.scene, Scene.BRIEFING)
        self.assertEqual(self.game.level_index, 2)

        self.game.scene = Scene.MENU
        self.press(pygame.K_KP4, unicode="")
        self.assertEqual(self.game.scene, Scene.BRIEFING)
        self.assertEqual(self.game.level_index, 3)

        self.game.scene = Scene.MENU
        self.press(pygame.K_5, unicode="5")
        self.assertEqual(self.game.scene, Scene.BRIEFING)
        self.assertEqual(self.game.level_index, 4)

        self.game.scene = Scene.MENU
        self.press(pygame.K_KP5, unicode="")
        self.assertEqual(self.game.scene, Scene.BRIEFING)
        self.assertEqual(self.game.level_index, 4)

    def test_chapter_one_completion_routes_to_chapter_two_story(self) -> None:
        self.game._load_level(0)
        self.game.scene = Scene.WON

        self.press(pygame.K_RETURN, unicode="\r")

        self.assertEqual(self.game.level_index, 1)
        self.assertEqual(self.game.scene, Scene.BRIEFING)

    def test_campaign_completion_advances_through_all_five_chapters(self) -> None:
        for index in range(4):
            with self.subTest(level=index):
                self.game._load_level(index)
                self.game.scene = Scene.WON
                self.press(pygame.K_RETURN, unicode="\r")
                self.assertEqual(self.game.level_index, index + 1)
                self.assertEqual(self.game.scene, Scene.BRIEFING)

        self.game._load_level(4)
        self.game.scene = Scene.WON
        self.press(pygame.K_KP_ENTER, unicode="")
        self.assertEqual(self.game.level_index, 0)
        self.assertEqual(self.game.scene, Scene.BRIEFING)

    def test_final_chapter_retry_still_replays_the_boss_level(self) -> None:
        self.game._load_level(4)
        self.game.scene = Scene.WON

        self.press(pygame.K_r, unicode="r")

        self.assertEqual(self.game.level_index, 4)
        self.assertEqual(self.game.scene, Scene.PLAYING)

    def test_all_briefings_and_endings_render_headlessly(self) -> None:
        for index in range(len(MISSION_STORIES)):
            with self.subTest(level=index):
                self.game._begin_mission(index)
                self.game._draw()
                self.game.scene = Scene.WON
                self.game._draw()
                self.assertEqual(self.game.screen.get_size(), settings.SCREEN_SIZE)

    def test_fullscreen_toggle_preserves_current_mission_state(self) -> None:
        self.game._load_level(3)
        self.game.player.give_keycard()
        self.game.elapsed = 12.5
        scene = self.game.scene

        self.game._toggle_fullscreen()

        self.assertTrue(self.game.fullscreen)
        self.assertEqual(self.game.screen.get_size(), settings.SCREEN_SIZE)
        self.assertEqual(self.game.scene, scene)
        self.assertEqual(self.game.level_index, 3)
        self.assertTrue(self.game.player.has_keycard())
        self.assertEqual(self.game.elapsed, 12.5)

    def test_alt_enter_toggles_even_while_hacking_without_submitting(self) -> None:
        self.game._load_level(1)
        self.game.player.give_keycard()
        terminal = self.game.terminals[0]
        puzzle = terminal.begin_hack(self.game.player, sequence=(1, 2, 3, 4))
        self.assertIsNotNone(puzzle)
        self.game.active_terminal = terminal
        self.game.hacking_puzzle = puzzle
        self.game.scene = Scene.HACKING
        attempts = puzzle.attempts_remaining

        self.press(pygame.K_RETURN, unicode="\r", mod=pygame.KMOD_ALT)

        self.assertTrue(self.game.fullscreen)
        self.assertEqual(self.game.scene, Scene.HACKING)
        self.assertIs(self.game.hacking_puzzle, puzzle)
        self.assertEqual(puzzle.attempts_remaining, attempts)

    def test_hacking_accepts_number_pad_without_unicode_text(self) -> None:
        self.game._load_level(1)
        self.game.player.give_keycard()
        terminal = self.game.terminals[0]
        puzzle = terminal.begin_hack(self.game.player, sequence=(1, 2, 3, 4))
        self.assertIsNotNone(puzzle)
        puzzle.update(puzzle.reveal_duration)
        self.game.active_terminal = terminal
        self.game.hacking_puzzle = puzzle
        self.game.scene = Scene.HACKING

        self.game._handle_hacking_key(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP1, unicode="")
        )

        self.assertEqual(puzzle.entered, ("1",))

    def test_f11_toggles_from_story_screen(self) -> None:
        self.game._begin_mission(0)
        self.press(pygame.K_F11)

        self.assertTrue(self.game.fullscreen)
        self.assertEqual(self.game.scene, Scene.BRIEFING)


if __name__ == "__main__":
    unittest.main()
