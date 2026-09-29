"""Sprite loading and procedural art for Robot Lab Escape.

Production art can be exported to ``assets/sprites`` with the filenames from
``spec/assets_manifest.json``.  Missing files resolve to cached procedural
surfaces, keeping the prototype fully playable during the art pass.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import pygame


ROOT = Path(__file__).resolve().parent
CYAN = pygame.Color("#28D7FF")
RED = pygame.Color("#FF3B3B")
GREEN = pygame.Color("#27D766")
YELLOW = pygame.Color("#F8C431")
BLUE = pygame.Color("#377DFF")
NAVY = pygame.Color("#0A1624")
STEEL = pygame.Color("#46586B")
WHITE = pygame.Color("#EEF5FB")


class SpriteLibrary:
    """Load named sprites and provide consistent procedural replacements."""

    def __init__(
        self,
        root: str | Path | None = None,
        tile_size: int = 48,
        *,
        preload: bool = False,
    ) -> None:
        self.root = Path(root) if root is not None else ROOT / "assets" / "sprites"
        self.tile_size = int(tile_size)
        self._cache: dict[tuple[str, tuple[int, int]], pygame.Surface] = {}
        self._manifest_names: tuple[str, ...] | None = None
        if preload:
            for name in self.manifest_names:
                self.get(name)

    @property
    def manifest_names(self) -> tuple[str, ...]:
        if self._manifest_names is None:
            path = ROOT / "spec" / "assets_manifest.json"
            names: list[str] = []
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))

                def collect(value: object) -> None:
                    if isinstance(value, str) and value.lower().endswith(".png"):
                        names.append(value)
                    elif isinstance(value, dict):
                        for child in value.values():
                            collect(child)
                    elif isinstance(value, list):
                        for child in value:
                            collect(child)

                collect(data)
            self._manifest_names = tuple(dict.fromkeys(names))
        return self._manifest_names

    def has(self, name: str) -> bool:
        return (self.root / name).is_file()

    def get(
        self,
        name: str,
        size: int | tuple[int, int] | None = None,
        *,
        fallback: bool = True,
    ) -> pygame.Surface | None:
        dimensions = self._size(size)
        key = (name, dimensions)
        if key in self._cache:
            return self._cache[key]

        path = self.root / name
        surface: pygame.Surface | None = None
        if path.is_file():
            try:
                surface = pygame.image.load(path)
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
                if surface.get_size() != dimensions:
                    surface = pygame.transform.smoothscale(surface, dimensions)
            except (OSError, pygame.error):
                surface = None
        if surface is None and fallback:
            surface = self._fallback(name, dimensions)
        if surface is not None:
            self._cache[key] = surface
        return surface

    image = get

    def _size(self, size: int | tuple[int, int] | None) -> tuple[int, int]:
        if size is None:
            return self.tile_size, self.tile_size
        return (size, size) if isinstance(size, int) else tuple(map(int, size))

    def _fallback(self, name: str, size: tuple[int, int]) -> pygame.Surface:
        lower = name.casefold()
        if lower.startswith("player_"):
            direction = next((d for d in ("down", "up", "left", "right") if d in lower), "down")
            return self.player_robot(direction, "walk" in lower, 1 if lower.endswith("1.png") else 0, size)
        if lower.startswith("security_"):
            direction = next((d for d in ("down", "up", "left", "right") if d in lower), "down")
            return self.security_bot(direction, "chase" in lower, size)
        if lower.startswith("hunter_"):
            return self.hunter_x("attack" in lower, size)
        if lower.startswith("warden_prime"):
            return self.warden_prime(size=size)
        if lower.startswith("cctv_"):
            direction = next((d for d in ("down", "up", "left", "right") if d in lower), "down")
            return self.cctv(direction, False, size)
        if lower.startswith("floor_"):
            return self.floor_tile(abs(hash(lower)) % 4, size)
        if lower.startswith("wall_"):
            return self.wall_tile(abs(hash(lower)) % 3, size)
        if lower in {"door_open.png", "door_closed.png", "door_locked.png"}:
            return self.door("open" in lower, "locked" in lower, size)
        if lower in {"exit_door.png", "elevator.png"}:
            return self.exit_door(size)
        if lower.startswith("keycard_"):
            return self.keycard(lower.removeprefix("keycard_").removesuffix(".png"), size)
        if lower == "battery_pack.png":
            return self.battery_pack(size)
        if lower == "emp_charge.png":
            return self.emp_charge(size)
        if lower == "terminal.png":
            return self.terminal(False, size)
        if lower == "effect_emp.png":
            return self.emp_wave(min(size) // 2)
        return self.placeholder(name, size)

    def floor_tile(
        self, variant: int = 0, size: int | tuple[int, int] | None = None
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        base = 27 + (variant % 3) * 3
        surface.fill((base, base + 10, base + 20))
        pygame.draw.line(surface, (55, 70, 84), (0, 0), (dimensions[0], 0), 1)
        pygame.draw.line(surface, (14, 26, 38), (0, dimensions[1] - 1), (dimensions[0], dimensions[1] - 1), 2)
        pygame.draw.line(surface, (14, 26, 38), (dimensions[0] - 1, 0), (dimensions[0] - 1, dimensions[1]), 1)
        if variant % 4 == 0:
            for point in ((7, 7), (dimensions[0] - 7, dimensions[1] - 7)):
                pygame.draw.circle(surface, (83, 98, 109), point, 2)
        return surface

    def wall_tile(
        self, variant: int = 0, size: int | tuple[int, int] | None = None
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        rect = surface.get_rect()
        pygame.draw.rect(surface, (38, 54, 70), rect)
        pygame.draw.rect(surface, (76, 95, 112), rect, 2)
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(surface, (27, 41, 55), inner, border_radius=3)
        pygame.draw.line(surface, (100, 120, 136), inner.topleft, inner.topright, 2)
        seam_x = dimensions[0] // 2 + (variant - 1) * 3
        pygame.draw.line(surface, (18, 29, 40), (seam_x, 6), (seam_x, dimensions[1] - 6), 1)
        pygame.draw.circle(surface, (126, 140, 150), (7, 7), 2)
        pygame.draw.circle(surface, (16, 26, 36), (dimensions[0] - 7, dimensions[1] - 7), 2)
        return surface

    def player_robot(
        self,
        direction: str = "down",
        moving: bool = False,
        frame: int = 0,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        cx, cy = dimensions[0] // 2, dimensions[1] // 2
        bob = 1 if moving and frame % 2 else 0
        pygame.draw.ellipse(surface, (0, 0, 0, 75), (cx - 15, cy + 13, 30, 8))
        body = pygame.Rect(cx - 12, cy - 10 + bob, 24, 28)
        pygame.draw.rect(surface, (218, 231, 239), body, border_radius=9)
        pygame.draw.rect(surface, (47, 70, 88), body, 2, border_radius=9)
        head = pygame.Rect(cx - 14, cy - 18 + bob, 28, 17)
        pygame.draw.rect(surface, (232, 241, 246), head, border_radius=7)
        pygame.draw.rect(surface, (38, 58, 73), head, 2, border_radius=7)
        visor = head.inflate(-8, -7)
        pygame.draw.rect(surface, (9, 26, 39), visor, border_radius=3)
        eye_x = visor.centerx + ({"left": -4, "right": 4}.get(direction, 0))
        pygame.draw.circle(surface, CYAN, (eye_x, visor.centery), 3)
        pygame.draw.circle(surface, (177, 248, 255), (eye_x, visor.centery), 1)
        pygame.draw.circle(surface, CYAN, (cx, body.centery + 2), 4)
        leg_shift = 2 if moving and frame % 2 else 0
        pygame.draw.rect(surface, (50, 70, 86), (cx - 10 - leg_shift, cy + 14, 8, 7), border_radius=2)
        pygame.draw.rect(surface, (50, 70, 86), (cx + 2 + leg_shift, cy + 14, 8, 7), border_radius=2)
        return surface

    def security_bot(
        self,
        direction: str = "down",
        alerted: bool = False,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        cx, cy = dimensions[0] // 2, dimensions[1] // 2
        pygame.draw.ellipse(surface, (0, 0, 0, 80), (cx - 15, cy + 13, 30, 8))
        body = pygame.Rect(cx - 13, cy - 12, 26, 31)
        pygame.draw.rect(surface, (83, 94, 105), body, border_radius=9)
        pygame.draw.rect(surface, (22, 29, 37), body, 3, border_radius=9)
        visor = pygame.Rect(cx - 11, cy - 8, 22, 9)
        pygame.draw.rect(surface, (28, 8, 13), visor, border_radius=3)
        eye_x = visor.centerx + ({"left": -5, "right": 5}.get(direction, 0))
        color = RED if alerted else (236, 70, 70)
        pygame.draw.circle(surface, color, (eye_x, visor.centery), 3 if alerted else 2)
        pygame.draw.rect(surface, (38, 46, 55), (cx - 17, cy + 2, 7, 13), border_radius=3)
        pygame.draw.rect(surface, (38, 46, 55), (cx + 10, cy + 2, 7, 13), border_radius=3)
        return surface

    def hunter_x(
        self,
        alerted: bool = False,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        cx, cy = dimensions[0] // 2, dimensions[1] // 2
        pygame.draw.ellipse(surface, (0, 0, 0, 90), (cx - 20, cy + 14, 40, 9))
        body = pygame.Rect(cx - 16, cy - 13, 32, 31)
        pygame.draw.ellipse(surface, (177, 76, 30), body)
        pygame.draw.ellipse(surface, (51, 29, 25), body, 3)
        visor = pygame.Rect(cx - 12, cy - 8, 24, 8)
        pygame.draw.rect(surface, (35, 8, 8), visor, border_radius=3)
        pygame.draw.circle(surface, RED, visor.center, 4 if alerted else 3)
        arm_color = (111, 48, 29)
        pygame.draw.circle(surface, arm_color, (cx - 19, cy + 3), 8)
        pygame.draw.circle(surface, arm_color, (cx + 19, cy + 3), 8)
        pygame.draw.line(surface, YELLOW if alerted else (211, 103, 43), (cx - 18, cy + 7), (cx - 23, cy + 17), 3)
        pygame.draw.line(surface, YELLOW if alerted else (211, 103, 43), (cx + 18, cy + 7), (cx + 23, cy + 17), 3)
        return surface

    def warden_prime(
        self,
        *,
        shielded: bool = True,
        damaged: bool = False,
        defeated: bool = False,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        """Draw the armored WARDEN PRIME chassis and its shield state."""

        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        cx, cy = dimensions[0] // 2, dimensions[1] // 2
        scale = max(1, min(dimensions) // 18)

        pygame.draw.ellipse(
            surface,
            (0, 0, 0, 105),
            (cx - 27, cy + 19, 54, 12),
        )
        body_color = (50, 52, 65) if defeated else (99, 42, 68) if damaged else (66, 58, 84)
        edge_color = (77, 90, 101) if defeated else (220, 67, 91)
        body = pygame.Rect(cx - 23, cy - 18, 46, 43)
        pygame.draw.rect(surface, body_color, body, border_radius=10)
        pygame.draw.rect(surface, edge_color, body, 3, border_radius=10)

        for side in (-1, 1):
            shoulder = (cx + side * 28, cy - 4)
            pygame.draw.circle(surface, (45, 43, 55), shoulder, 11)
            pygame.draw.circle(surface, edge_color, shoulder, 2)
            pygame.draw.line(
                surface,
                (103, 74, 88),
                shoulder,
                (cx + side * 31, cy + 19),
                max(3, scale),
            )

        visor = pygame.Rect(cx - 18, cy - 11, 36, 10)
        pygame.draw.rect(surface, (20, 8, 18), visor, border_radius=4)
        core_color = STEEL if defeated else YELLOW if shielded else RED
        pygame.draw.circle(surface, core_color, visor.center, 5)
        pygame.draw.circle(surface, WHITE, visor.center, 2)
        pygame.draw.circle(surface, core_color, (cx, cy + 11), 7, 2)

        if shielded and not defeated:
            radius = min(dimensions) // 2 - 3
            pygame.draw.circle(surface, (*CYAN[:3], 85), (cx, cy), radius, 3)
            for angle in range(0, 360, 60):
                point = pygame.Vector2(radius - 1, 0).rotate(angle) + (cx, cy)
                pygame.draw.circle(surface, CYAN, point, 2)
        return surface

    def cctv(
        self,
        direction: str = "down",
        disabled: bool = False,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        cx, cy = dimensions[0] // 2, dimensions[1] // 2
        offsets = {"down": (0, 6), "up": (0, -6), "left": (-7, 0), "right": (7, 0)}
        dx, dy = offsets.get(direction, (0, 6))
        pygame.draw.line(surface, (113, 129, 142), (cx, cy - 14), (cx, cy - 5), 4)
        body = pygame.Rect(cx - 14 + dx, cy - 7 + dy, 28, 14)
        pygame.draw.rect(surface, (115, 126, 137), body, border_radius=4)
        pygame.draw.rect(surface, (30, 39, 48), body, 2, border_radius=4)
        lens = (body.right - 4, body.centery) if direction != "left" else (body.left + 4, body.centery)
        pygame.draw.circle(surface, STEEL if disabled else RED, lens, 3)
        return surface

    def terminal(
        self,
        hacked: bool = False,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        base = pygame.Rect(dimensions[0] // 5, dimensions[1] // 2, dimensions[0] * 3 // 5, dimensions[1] // 3)
        pygame.draw.rect(surface, (55, 67, 79), base, border_radius=4)
        screen = pygame.Rect(5, 5, dimensions[0] - 10, dimensions[1] // 2)
        pygame.draw.rect(surface, (13, 31, 44), screen, border_radius=4)
        color = GREEN if hacked else CYAN
        pygame.draw.rect(surface, color, screen, 2, border_radius=4)
        pygame.draw.line(surface, color, (screen.x + 6, screen.centery), (screen.right - 6, screen.centery), 2)
        pygame.draw.circle(surface, color, (base.centerx, base.centery), 3)
        return surface

    def emp_charge(self, size: int | tuple[int, int] | None = None) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        center = dimensions[0] // 2, dimensions[1] // 2
        radius = max(5, min(dimensions) // 3)
        pygame.draw.circle(surface, (42, 57, 73), center, radius + 3)
        pygame.draw.circle(surface, CYAN, center, radius, 3)
        pygame.draw.circle(surface, (202, 250, 255), center, max(2, radius // 3))
        for angle in range(0, 360, 90):
            direction = pygame.Vector2(1, 0).rotate(angle)
            start = pygame.Vector2(center) + direction * (radius + 2)
            end = pygame.Vector2(center) + direction * (radius + 7)
            pygame.draw.line(surface, CYAN, start, end, 2)
        return surface

    def emp_wave(self, radius: int, alpha: int = 150) -> pygame.Surface:
        radius = max(2, int(radius))
        surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        center = radius + 2, radius + 2
        pygame.draw.circle(surface, (*CYAN[:3], max(0, min(255, alpha))), center, radius, 3)
        pygame.draw.circle(surface, (*WHITE[:3], max(0, min(255, alpha // 2))), center, max(1, radius - 5), 1)
        return surface

    def keycard(
        self, color: str = "blue", size: int | tuple[int, int] | None = None
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        colors = {"blue": BLUE, "red": RED, "white": WHITE}
        card = pygame.Rect(3, dimensions[1] // 4, dimensions[0] - 6, dimensions[1] // 2)
        pygame.draw.rect(surface, colors.get(color, BLUE), card, border_radius=4)
        pygame.draw.rect(surface, WHITE, card, 2, border_radius=4)
        pygame.draw.rect(surface, (205, 235, 255), (card.x + 5, card.centery - 2, card.width // 3, 4), border_radius=2)
        return surface

    def battery_pack(self, size: int | tuple[int, int] | None = None) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        body = pygame.Rect(dimensions[0] // 4, 6, dimensions[0] // 2, dimensions[1] - 10)
        pygame.draw.rect(surface, (35, 57, 68), body, border_radius=6)
        pygame.draw.rect(surface, GREEN, body.inflate(-6, -7), border_radius=4)
        terminal = pygame.Rect(0, 0, max(6, body.width // 3), 4)
        terminal.midbottom = body.midtop
        pygame.draw.rect(surface, WHITE, terminal, border_radius=2)
        pygame.draw.polygon(surface, (239, 255, 185), [(body.centerx + 2, 13), (body.centerx - 4, body.centery), (body.centerx, body.centery), (body.centerx - 2, body.bottom - 7), (body.centerx + 5, body.centery - 2), (body.centerx + 1, body.centery - 2)])
        return surface

    def door(
        self,
        opened: bool = False,
        locked: bool = True,
        size: int | tuple[int, int] | None = None,
    ) -> pygame.Surface:
        dimensions = self._size(size)
        surface = pygame.Surface(dimensions, pygame.SRCALPHA)
        rect = surface.get_rect().inflate(-2, -1)
        if opened:
            pygame.draw.rect(surface, (35, 78, 72), rect, 3, border_radius=4)
            pygame.draw.line(surface, GREEN, (6, 8), (6, dimensions[1] - 7), 3)
            pygame.draw.line(surface, GREEN, (dimensions[0] - 7, 8), (dimensions[0] - 7, dimensions[1] - 7), 3)
            return surface
        pygame.draw.rect(surface, (47, 59, 74), rect, border_radius=4)
        pygame.draw.rect(surface, (120, 140, 154), rect, 3, border_radius=4)
        pygame.draw.line(surface, (20, 27, 37), (dimensions[0] // 2, 5), (dimensions[0] // 2, dimensions[1] - 5), 4)
        pygame.draw.rect(surface, RED if locked else GREEN, (dimensions[0] // 2 - 6, 5, 12, 4), border_radius=2)
        return surface

    def exit_door(self, size: int | tuple[int, int] | None = None) -> pygame.Surface:
        dimensions = self._size(size)
        surface = self.door(False, False, dimensions)
        sign = pygame.Rect(4, 3, dimensions[0] - 8, max(10, dimensions[1] // 5))
        pygame.draw.rect(surface, (9, 45, 31), sign, border_radius=2)
        pygame.draw.rect(surface, GREEN, sign, 2, border_radius=2)
        # An arrow remains readable even at small sizes and avoids font setup.
        cx, cy = sign.center
        pygame.draw.line(surface, GREEN, (cx - 7, cy), (cx + 5, cy), 2)
        pygame.draw.polygon(surface, GREEN, [(cx + 6, cy), (cx + 1, cy - 4), (cx + 1, cy + 4)])
        return surface

    def detection_cone(
        self,
        angle: float = 0.0,
        length: int = 180,
        width: float = 55.0,
    ) -> pygame.Surface:
        radius = int(length)
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        center = pygame.Vector2(radius, radius)
        half = math.radians(width / 2)
        heading = math.radians(angle)
        points = [center]
        for step in range(13):
            ray = heading - half + (2 * half * step / 12)
            points.append(center + pygame.Vector2(math.cos(ray), math.sin(ray)) * radius)
        pygame.draw.polygon(surface, (*RED[:3], 42), points)
        pygame.draw.lines(surface, (*RED[:3], 105), False, points[1:], 1)
        return surface

    def glow(
        self, color: pygame.Color | tuple[int, int, int], radius: int, alpha: int = 90
    ) -> pygame.Surface:
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        rgb = pygame.Color(color)
        for current in range(radius, 0, -3):
            strength = int(alpha * (1 - current / radius) ** 1.5)
            pygame.draw.circle(surface, (*rgb[:3], strength), (radius, radius), current)
        return surface

    def ui_panel(
        self,
        size: tuple[int, int],
        border: pygame.Color | tuple[int, int, int] = CYAN,
        fill: pygame.Color | tuple[int, int, int] = NAVY,
    ) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (*pygame.Color(fill)[:3], 235), surface.get_rect(), border_radius=7)
        pygame.draw.rect(surface, pygame.Color(border), surface.get_rect(), 2, border_radius=7)
        return surface

    def placeholder(self, name: str, size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        rect = surface.get_rect().inflate(-4, -4)
        pygame.draw.rect(surface, (43, 59, 74), rect, border_radius=5)
        pygame.draw.rect(surface, STEEL, rect, 2, border_radius=5)
        pygame.draw.line(surface, YELLOW, rect.topleft, rect.bottomright, 2)
        pygame.draw.line(surface, YELLOW, rect.topright, rect.bottomleft, 2)
        return surface


AssetManager = SpriteLibrary

__all__ = ["AssetManager", "SpriteLibrary"]
