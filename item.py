"""Collectible item models for Robot Lab Escape."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pygame

try:
    import settings as _settings
except ImportError:  # pragma: no cover
    _settings = None


def _setting(name: str, default: Any) -> Any:
    return getattr(_settings, name, default) if _settings is not None else default


DEFAULT_TILE_SIZE = int(_setting("TILE_SIZE", 32))
DEFAULT_BATTERY_AMOUNT = float(_setting("BATTERY_PICKUP_AMOUNT", 35.0))


class WorldItem(pygame.sprite.Sprite):
    """Base class for a resettable, non-solid world pickup."""

    kind = "item"
    blocks = False
    blocks_los = False
    solid = False

    def __init__(
        self,
        position: Sequence[float] | pygame.Vector2,
        *,
        size: int | tuple[int, int] = 22,
    ) -> None:
        super().__init__()
        dimensions = (size, size) if isinstance(size, int) else size
        self.image = pygame.Surface(dimensions, pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(round(position[0]), round(position[1])))
        self.start_position = pygame.Vector2(position)
        self.position = pygame.Vector2(position)
        self.active = True

    @property
    def collected(self) -> bool:
        return not self.active

    @classmethod
    def from_tile(
        cls,
        tile: Sequence[int],
        *,
        tile_size: int = DEFAULT_TILE_SIZE,
        **kwargs: Any,
    ) -> "WorldItem":
        center = ((tile[0] + 0.5) * tile_size, (tile[1] + 0.5) * tile_size)
        return cls(center, **kwargs)

    def can_interact(self, player: object, padding: int = 18) -> bool:
        if not self.active:
            return False
        player_rect = getattr(player, "rect", None)
        return isinstance(player_rect, pygame.Rect) and player_rect.inflate(
            padding * 2, padding * 2
        ).colliderect(self.rect)

    def interact(self, player: object) -> bool:
        raise NotImplementedError

    collect = interact

    def reset(self) -> None:
        self.position.update(self.start_position)
        self.rect.center = (round(self.position.x), round(self.position.y))
        self.active = True

    def draw(
        self,
        surface: pygame.Surface,
        offset: Sequence[float] | pygame.Vector2 = (0.0, 0.0),
    ) -> None:
        if not self.active:
            return
        draw_rect = self.image.get_rect(
            center=(round(self.rect.centerx + offset[0]), round(self.rect.centery + offset[1]))
        )
        surface.blit(self.image, draw_rect)


class Keycard(WorldItem):
    """A colored access card.  The MVP uses ``color='blue'``."""

    kind = "keycard"

    _COLORS = {
        "blue": pygame.Color("#2F7DF4"),
        "red": pygame.Color("#E94A4A"),
        "white": pygame.Color("#E5EDF2"),
    }

    def __init__(
        self,
        position: Sequence[float] | pygame.Vector2,
        color: str = "blue",
        *,
        size: int | tuple[int, int] = (26, 16),
    ) -> None:
        self.color = color.casefold()
        super().__init__(position, size=size)
        self._paint()

    @property
    def key_color(self) -> str:
        return self.color

    def _paint(self) -> None:
        self.image.fill((0, 0, 0, 0))
        outer = self.image.get_rect().inflate(-1, -1)
        pygame.draw.rect(
            self.image,
            self._COLORS.get(self.color, pygame.Color("#A979D8")),
            outer,
            border_radius=3,
        )
        pygame.draw.rect(self.image, (225, 239, 248), outer, width=2, border_radius=3)
        stripe = pygame.Rect(outer.left + 4, outer.centery - 1, max(4, outer.width // 3), 3)
        pygame.draw.rect(self.image, (240, 250, 255), stripe, border_radius=1)

    def interact(self, player: object) -> bool:
        if not self.active:
            return False
        give = getattr(player, "give_keycard", None) or getattr(player, "add_keycard", None)
        if not callable(give):
            return False
        give(self.color)
        self.active = False
        return True

    collect = interact


class BatteryPack(WorldItem):
    """A battery pickup that remains available when the player's charge is full."""

    kind = "battery"

    def __init__(
        self,
        position: Sequence[float] | pygame.Vector2,
        amount: float = DEFAULT_BATTERY_AMOUNT,
        *,
        size: int | tuple[int, int] = (18, 26),
    ) -> None:
        self.amount = max(0.0, float(amount))
        super().__init__(position, size=size)
        self._paint()

    def _paint(self) -> None:
        self.image.fill((0, 0, 0, 0))
        body = self.image.get_rect().inflate(-3, -4)
        body.y += 2
        pygame.draw.rect(self.image, (34, 57, 68), body, border_radius=4)
        fill = body.inflate(-4, -4)
        pygame.draw.rect(self.image, (52, 221, 121), fill, border_radius=2)
        terminal = pygame.Rect(0, 0, max(5, body.width // 3), 3)
        terminal.midbottom = body.midtop
        pygame.draw.rect(self.image, (191, 211, 220), terminal, border_radius=1)
        bolt = [
            (fill.centerx + 1, fill.top + 2),
            (fill.centerx - 3, fill.centery),
            (fill.centerx, fill.centery),
            (fill.centerx - 1, fill.bottom - 2),
            (fill.centerx + 4, fill.centery - 1),
            (fill.centerx + 1, fill.centery - 1),
        ]
        pygame.draw.polygon(self.image, (237, 255, 188), bolt)

    def interact(self, player: object) -> bool:
        if not self.active:
            return False
        restore = getattr(player, "restore_battery", None)
        if not callable(restore):
            return False
        restored = float(restore(self.amount))
        if restored <= 0.0:
            return False
        self.active = False
        return True

    collect = interact


Item = WorldItem

__all__ = ["BatteryPack", "Item", "Keycard", "WorldItem"]
