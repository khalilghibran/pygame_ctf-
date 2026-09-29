"""HUD and screen overlays for Robot Lab Escape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pygame


NAVY = (10, 22, 36)
PANEL = (13, 34, 53)
STEEL = (70, 88, 107)
LIGHT = (199, 215, 225)
WHITE = (244, 250, 255)
CYAN = (40, 215, 255)
BLUE = (42, 119, 238)
RED = (255, 59, 59)
GREEN = (39, 215, 102)
YELLOW = (248, 196, 49)


class FontBook:
    """Small font cache that uses fonts available on every pygame install."""

    def __init__(self) -> None:
        self._cache: dict[tuple[int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._cache:
            self._cache[key] = pygame.font.SysFont(
                "consolas,couriernew,monospace", size, bold=bold
            )
        return self._cache[key]


@dataclass(slots=True)
class Toast:
    text: str = ""
    color: tuple[int, int, int] = CYAN
    remaining: float = 0.0

    def show(
        self, text: str, color: tuple[int, int, int] = CYAN, duration: float = 2.2
    ) -> None:
        self.text = text
        self.color = color
        self.remaining = duration

    def update(self, dt: float) -> None:
        self.remaining = max(0.0, self.remaining - dt)


class UI:
    """Draw the HUD, title, pause, result, and interaction screens."""

    def __init__(self, screen_size: tuple[int, int]) -> None:
        self.width, self.height = screen_size
        self.fonts = FontBook()
        self.toast = Toast()

    @staticmethod
    def panel(
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        border: tuple[int, int, int] = STEEL,
        fill: tuple[int, int, int] = PANEL,
        alpha: int = 235,
        radius: int = 7,
    ) -> None:
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*fill, alpha), layer.get_rect(), border_radius=radius)
        pygame.draw.rect(layer, (*border, min(255, alpha + 15)), layer.get_rect(), 2, border_radius=radius)
        pygame.draw.line(layer, (*WHITE, 45), (8, 4), (rect.width - 8, 4), 1)
        surface.blit(layer, rect)

    def text(
        self,
        surface: pygame.Surface,
        value: str,
        pos: tuple[int, int],
        *,
        size: int = 20,
        color: tuple[int, int, int] = WHITE,
        bold: bool = False,
        anchor: str = "topleft",
    ) -> pygame.Rect:
        image = self.fonts.get(size, bold).render(value, True, color)
        rect = image.get_rect()
        setattr(rect, anchor, pos)
        surface.blit(image, rect)
        return rect

    def bar(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        value: float,
        maximum: float,
        color: tuple[int, int, int],
    ) -> None:
        pygame.draw.rect(surface, (5, 14, 24), rect, border_radius=5)
        ratio = max(0.0, min(1.0, value / maximum if maximum else 0.0))
        inner = rect.inflate(-4, -4)
        fill = inner.copy()
        fill.width = round(inner.width * ratio)
        if fill.width:
            pygame.draw.rect(surface, color, fill, border_radius=3)
            gleam = pygame.Rect(fill.x + 2, fill.y + 2, max(0, fill.width - 4), 2)
            if gleam.width:
                pygame.draw.rect(surface, tuple(min(255, c + 55) for c in color), gleam)
        pygame.draw.rect(surface, STEEL, rect, 2, border_radius=5)

    def draw_hud(
        self,
        surface: pygame.Surface,
        *,
        battery: float,
        max_battery: float,
        has_keycard: bool,
        security_state: str,
        objective: str,
        elapsed: float,
        prompt: str = "",
        emp_charges: int = 0,
        alarm_level: int = 0,
        level_label: str = "LAB A-1",
        terminal_hacked: bool | None = None,
        terminal_progress: tuple[int, int] | None = None,
        boss_name: str | None = None,
        boss_health: int = 0,
        boss_max_health: int = 0,
        boss_shielded: bool = False,
        boss_defeated: bool = False,
        dash_active: bool = False,
    ) -> None:
        left = pygame.Rect(28, 18, 410, 82)
        middle = pygame.Rect(454, 18, 524, 82)
        right = pygame.Rect(994, 18, 258, 82)
        self.panel(surface, left, border=CYAN)
        self.panel(surface, middle)
        state_color = (
            RED
            if "CHASE" in security_state
            else YELLOW
            if "SEARCH" in security_state
            else CYAN
        )
        self.panel(surface, right, border=state_color)

        power_label = "RX-01 POWER // DASH" if dash_active else "RX-01 POWER"
        self.text(surface, power_label, (45, 31), size=16, color=CYAN, bold=True)
        self.text(surface, f"EMP x{emp_charges}", (421, 31), size=13, color=CYAN if emp_charges else STEEL, bold=True, anchor="topright")
        self.bar(surface, pygame.Rect(45, 56, 275, 24), battery, max_battery, CYAN if battery > 25 else RED)
        self.text(surface, f"{battery:05.1f}%", (421, 68), size=16, anchor="midright")

        self.text(surface, "OBJECTIVE", (472, 30), size=14, color=YELLOW, bold=True)
        key_text = "KEY: ACQUIRED" if has_keycard else "KEY: MISSING"
        if terminal_hacked is not None:
            if terminal_hacked:
                key_text += "  //  NET: OFFLINE"
            elif terminal_progress is not None:
                key_text += f"  //  NET: {terminal_progress[0]}/{terminal_progress[1]}"
            else:
                key_text += "  //  NET: LOCKED"
        self.text(surface, key_text, (963, 30), size=12, color=BLUE if has_keycard else STEEL, anchor="topright")
        self.text(surface, objective, (472, 58), size=17, color=WHITE, bold=True)

        self.text(surface, "SECURITY", (1011, 30), size=14, color=state_color, bold=True)
        self.text(surface, level_label, (1235, 30), size=12, color=LIGHT, bold=True, anchor="topright")
        self.text(surface, security_state, (1011, 54), size=21, color=state_color, bold=True)
        mins, secs = divmod(int(elapsed), 60)
        alarm_text = "ALARM " + ("■" * alarm_level) + ("□" * max(0, 3 - alarm_level))
        self.text(surface, alarm_text, (1235, 63), size=11, color=RED if alarm_level else STEEL, anchor="topright")
        self.text(surface, f"RUN {mins:02d}:{secs:02d}", (1235, 88), size=12, color=LIGHT, anchor="bottomright")

        if boss_name:
            boss_box = pygame.Rect(0, 0, 500, 48)
            boss_box.midtop = (self.width // 2, 107)
            boss_color = GREEN if boss_defeated else CYAN if boss_shielded else RED
            self.panel(surface, boss_box, border=boss_color, fill=NAVY, alpha=248)
            self.text(
                surface,
                boss_name,
                (boss_box.x + 14, boss_box.y + 9),
                size=13,
                color=boss_color,
                bold=True,
            )
            status = (
                "DEFEATED"
                if boss_defeated
                else "SHIELD ONLINE"
                if boss_shielded
                else "CORE EXPOSED"
            )
            self.text(
                surface,
                status,
                (boss_box.right - 14, boss_box.y + 9),
                size=12,
                color=boss_color,
                bold=True,
                anchor="topright",
            )
            self.bar(
                surface,
                pygame.Rect(boss_box.x + 14, boss_box.y + 28, boss_box.width - 28, 12),
                boss_health,
                boss_max_health,
                boss_color,
            )

        if prompt:
            box = pygame.Rect(0, 0, min(620, max(320, len(prompt) * 12)), 44)
            box.midbottom = (self.width // 2, self.height - 18)
            self.panel(surface, box, border=CYAN, alpha=245)
            self.text(surface, prompt, box.center, size=17, color=WHITE, bold=True, anchor="center")

        if self.toast.remaining > 0 and self.toast.text:
            box = pygame.Rect(0, 0, min(760, max(360, len(self.toast.text) * 12)), 48)
            box.midtop = (self.width // 2, 112)
            self.panel(surface, box, border=self.toast.color, fill=NAVY, alpha=250)
            self.text(surface, self.toast.text, box.center, size=18, color=self.toast.color, bold=True, anchor="center")

    def draw_title(self, surface: pygame.Surface, pulse: float) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((*NAVY, 212))
        surface.blit(shade, (0, 0))
        title_y = self.height // 2 - 105
        glow_alpha = int(18 + 12 * pulse)
        glow = pygame.Surface((900, 105), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*CYAN, glow_alpha), glow.get_rect(), border_radius=30)
        pygame.draw.rect(glow, (*CYAN, 95), glow.get_rect(), 2, border_radius=30)
        surface.blit(glow, glow.get_rect(center=(self.width // 2, title_y + 40)))
        self.text(surface, "ROBOT LAB ESCAPE", (self.width // 2, title_y), size=54, color=WHITE, bold=True, anchor="midtop")
        self.text(surface, "SNEAK. SOLVE. POWER UP. ESCAPE.", (self.width // 2, title_y + 72), size=20, color=CYAN, bold=True, anchor="midtop")
        box = pygame.Rect(0, 0, 680, 218)
        box.center = (self.width // 2, self.height // 2 + 98)
        self.panel(surface, box, border=CYAN)
        self.text(surface, "ENTER  START CAMPAIGN", (box.centerx, box.y + 20), size=23, color=CYAN, bold=True, anchor="midtop")
        self.text(surface, "1  WAKE PROTOCOL       2  THE LAST SIGNAL", (box.centerx, box.y + 58), size=15, color=YELLOW, anchor="midtop")
        self.text(surface, "3  THE SLEEPING LINE   4  BREAK THE CYCLE", (box.centerx, box.y + 86), size=15, color=YELLOW, anchor="midtop")
        self.text(surface, "5 / NUMPAD 5  WARDEN PRIME // BOSS FIGHT", (box.centerx, box.y + 114), size=15, color=RED, bold=True, anchor="midtop")
        self.text(surface, "WASD / ARROWS  Move    E  Interact    SPACE  EMP", (box.centerx, box.y + 158), size=14, color=LIGHT, anchor="midtop")
        self.text(surface, "SHIFT  Dash    F11  Fullscreen    1-5  Select chapter    ESC / Q  Quit", (self.width // 2, self.height - 31), size=14, color=STEEL, anchor="midbottom")

    def draw_briefing(self, surface: pygame.Surface, story: object) -> None:
        """Draw one campaign chapter's story and play instructions."""

        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((2, 8, 15, 232))
        surface.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, 800, 532)
        box.center = (self.width // 2, self.height // 2)
        self.panel(surface, box, border=CYAN, fill=NAVY, alpha=252, radius=10)

        chapter = str(getattr(story, "chapter", "MISSION"))
        lab_label = str(getattr(story, "lab_label", "LAB"))
        title = str(getattr(story, "title", "BRIEFING"))
        transmission = str(getattr(story, "transmission", ""))
        self.text(surface, f"{chapter} // {lab_label}", (box.centerx, box.y + 24), size=16, color=YELLOW, bold=True, anchor="midtop")
        self.text(surface, title, (box.centerx, box.y + 55), size=38, color=CYAN, bold=True, anchor="midtop")
        self.text(surface, transmission, (box.centerx, box.y + 108), size=14, color=RED, bold=True, anchor="midtop")

        y = box.y + 150
        for line in tuple(getattr(story, "story_lines", ())):
            self.text(surface, str(line), (box.centerx, y), size=17, color=WHITE, anchor="midtop")
            y += 28

        divider_y = y + 7
        pygame.draw.line(surface, STEEL, (box.x + 70, divider_y), (box.right - 70, divider_y), 1)
        self.text(surface, "HOW THIS CHAPTER WORKS", (box.centerx, divider_y + 18), size=15, color=YELLOW, bold=True, anchor="midtop")
        y = divider_y + 52
        for index, line in enumerate(tuple(getattr(story, "mission_lines", ())), 1):
            self.text(surface, f"{index}. {line}", (box.x + 100, y), size=16, color=LIGHT, anchor="topleft")
            y += 30

        self.text(surface, "ENTER / SPACE  Begin mission", (box.centerx, box.bottom - 56), size=19, color=GREEN, bold=True, anchor="midtop")
        self.text(surface, "ESC  Return to menu    F11 / ALT+ENTER  Fullscreen", (box.centerx, box.bottom - 24), size=13, color=STEEL, anchor="midbottom")

    def draw_hacking(self, surface: pygame.Surface, puzzle: object) -> None:
        """Draw the terminal memory-sequence mini-game."""

        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((2, 8, 15, 225))
        surface.blit(shade, (0, 0))
        box = pygame.Rect(0, 0, 720, 410)
        box.center = (self.width // 2, self.height // 2)
        self.panel(surface, box, border=CYAN, fill=NAVY, alpha=252, radius=10)
        self.text(surface, "SECURITY TERMINAL", (box.centerx, box.y + 26), size=34, color=CYAN, bold=True, anchor="midtop")
        self.text(surface, "MEMORY-LINK AUTHENTICATION", (box.centerx, box.y + 72), size=16, color=LIGHT, anchor="midtop")

        raw_state = getattr(puzzle, "state", getattr(puzzle, "phase", "INPUT"))
        state = str(getattr(raw_state, "value", raw_state)).upper()
        sequence = tuple(str(value) for value in getattr(puzzle, "sequence", ()))
        entered = tuple(
            str(value)
            for value in getattr(
                puzzle,
                "input_buffer",
                getattr(puzzle, "entered", getattr(puzzle, "input", ())),
            )
        )
        reveal = "REVEAL" in state or "SHOW" in state

        if "SUCCESS" in state:
            self.text(surface, "ACCESS GRANTED", (box.centerx, box.y + 145), size=34, color=GREEN, bold=True, anchor="midtop")
            self.text(surface, "Security network disabled.", (box.centerx, box.y + 205), size=19, color=WHITE, anchor="midtop")
        else:
            label = "MEMORIZE SEQUENCE" if reveal else "ENTER SEQUENCE"
            self.text(surface, label, (box.centerx, box.y + 118), size=18, color=YELLOW if reveal else CYAN, bold=True, anchor="midtop")
            count = max(4, len(sequence))
            start_x = box.centerx - (count * 68 + (count - 1) * 12) // 2
            for index in range(count):
                token = pygame.Rect(start_x + index * 80, box.y + 165, 68, 72)
                active_color = YELLOW if reveal else CYAN
                pygame.draw.rect(surface, (8, 20, 31), token, border_radius=7)
                pygame.draw.rect(surface, active_color, token, 2, border_radius=7)
                value = "?"
                if reveal and index < len(sequence):
                    value = sequence[index]
                elif not reveal and index < len(entered):
                    value = entered[index]
                self.text(surface, value, token.center, size=34, color=WHITE, bold=True, anchor="center")

            attempts = int(getattr(puzzle, "attempts_remaining", getattr(puzzle, "attempts", 3)))
            self.text(surface, f"ATTEMPTS  {attempts}", (box.centerx, box.y + 264), size=16, color=RED if attempts <= 1 else LIGHT, anchor="midtop")
            if reveal:
                remaining = max(0.0, float(getattr(puzzle, "reveal_remaining", 0.0)))
                instruction = f"INPUT LOCKED // MEMORIZE ({remaining:.1f}s)"
                instruction_color = YELLOW
            else:
                instruction = "INPUT ACTIVE // 1-4 type    Backspace erase    Enter submit"
                instruction_color = GREEN
            self.text(surface, instruction, (box.centerx, box.y + 308), size=16, color=instruction_color, anchor="midtop")
        self.text(surface, "ESC  Disconnect", (box.centerx, box.bottom - 34), size=14, color=STEEL, anchor="midbottom")

    def draw_overlay(
        self,
        surface: pygame.Surface,
        title: str,
        subtitle: str,
        lines: Iterable[str],
        *,
        color: tuple[int, int, int] = CYAN,
    ) -> None:
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((2, 8, 15, 205))
        surface.blit(shade, (0, 0))
        lines = tuple(lines)
        height = 172 + len(lines) * 28
        box = pygame.Rect(0, 0, 660, height)
        box.center = (self.width // 2, self.height // 2)
        self.panel(surface, box, border=color, fill=NAVY, alpha=250, radius=10)
        self.text(surface, title, (box.centerx, box.y + 25), size=39, color=color, bold=True, anchor="midtop")
        self.text(surface, subtitle, (box.centerx, box.y + 80), size=18, color=WHITE, anchor="midtop")
        y = box.y + 124
        for line in lines:
            self.text(surface, line, (box.centerx, y), size=17, color=LIGHT, anchor="midtop")
            y += 28
