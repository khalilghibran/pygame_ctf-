"""Door and level-exit interaction models."""

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


def _rect_from_position(
    position: pygame.Rect | Sequence[float],
    size: int | tuple[int, int],
) -> pygame.Rect:
    if isinstance(position, pygame.Rect):
        return position.copy()
    if len(position) == 4:
        return pygame.Rect(position)
    dimensions = (size, size) if isinstance(size, int) else size
    return pygame.Rect(0, 0, *dimensions).copy().move(
        round(position[0] - dimensions[0] / 2),
        round(position[1] - dimensions[1] / 2),
    )


class Door:
    """A keycard-controlled solid tile.

    A two-value ``position`` is a world-space center; a ``pygame.Rect`` or a
    four-value sequence is used as an exact collision rectangle.
    """

    kind = "door"

    def __init__(
        self,
        position: pygame.Rect | Sequence[float],
        required_key: str | None = "blue",
        *,
        size: int | tuple[int, int] = DEFAULT_TILE_SIZE,
        initially_open: bool = False,
    ) -> None:
        self.rect = _rect_from_position(position, size)
        self.tile_size = int(size if isinstance(size, int) else size[0])
        self.required_key = required_key.casefold() if required_key else None
        self.initially_open = bool(initially_open)
        self.is_open = self.initially_open
        self.last_denied = False

    @classmethod
    def from_tile(
        cls,
        tile: Sequence[int],
        *,
        tile_size: int = DEFAULT_TILE_SIZE,
        **kwargs: Any,
    ) -> "Door":
        kwargs.setdefault("size", tile_size)
        return cls(
            pygame.Rect(tile[0] * tile_size, tile[1] * tile_size, tile_size, tile_size),
            **kwargs,
        )

    @property
    def blocks(self) -> bool:
        return not self.is_open

    @property
    def solid(self) -> bool:
        return self.blocks

    @property
    def blocks_los(self) -> bool:
        return not self.is_open

    @property
    def locked(self) -> bool:
        return not self.is_open

    @property
    def required_keycard(self) -> str | None:
        return self.required_key

    @property
    def tile(self) -> tuple[int, int]:
        return (self.rect.centerx // self.tile_size, self.rect.centery // self.tile_size)

    def can_open(self, player: object | None = None) -> bool:
        if self.is_open or self.required_key is None:
            return True
        if player is None:
            return False
        has_keycard = getattr(player, "has_keycard", None)
        if callable(has_keycard):
            return bool(has_keycard(self.required_key))
        inventory = getattr(player, "keycards", getattr(player, "inventory", ()))
        return self.required_key in inventory

    def interact(self, player: object | None = None) -> bool:
        """Try to open the door, returning whether it is open afterward."""

        if self.is_open:
            self.last_denied = False
            return True
        if not self.can_open(player):
            self.last_denied = True
            return False
        self.is_open = True
        self.last_denied = False
        return True

    unlock = interact

    def open(self) -> None:
        """Force the door open (useful for scripted events)."""

        self.is_open = True
        self.last_denied = False

    def reset(self) -> None:
        self.is_open = self.initially_open
        self.last_denied = False

    def draw(
        self,
        surface: pygame.Surface,
        offset: Sequence[float] | pygame.Vector2 = (0.0, 0.0),
    ) -> None:
        draw_rect = self.rect.move(round(offset[0]), round(offset[1]))
        if self.is_open:
            pygame.draw.rect(surface, (35, 78, 72), draw_rect, width=3, border_radius=3)
            inset = draw_rect.inflate(-10, -5)
            pygame.draw.rect(surface, (39, 166, 106), inset, width=2, border_radius=2)
            return
        pygame.draw.rect(surface, (48, 60, 75), draw_rect, border_radius=4)
        pygame.draw.rect(surface, (118, 139, 153), draw_rect, width=3, border_radius=4)
        seam = pygame.Rect(draw_rect.centerx - 2, draw_rect.top + 4, 4, draw_rect.height - 8)
        pygame.draw.rect(surface, (24, 31, 43), seam)
        indicator = (draw_rect.centerx, draw_rect.top + 7)
        color = (255, 59, 59) if self.required_key else (39, 215, 102)
        pygame.draw.circle(surface, color, indicator, 3)


class Exit(Door):
    """The key-gated exit.  A successful interaction sets ``activated``."""

    kind = "exit"

    def __init__(
        self,
        position: pygame.Rect | Sequence[float],
        required_key: str | None = "blue",
        *,
        size: int | tuple[int, int] = DEFAULT_TILE_SIZE,
    ) -> None:
        super().__init__(position, required_key, size=size, initially_open=False)
        self.activated = False

    @property
    def reached(self) -> bool:
        return self.activated

    def can_exit(self, player: object | None) -> bool:
        return self.can_open(player)

    def interact(self, player: object | None = None) -> bool:
        """Return ``True`` exactly when access is granted to the level exit."""

        if self.activated:
            return True
        if not self.can_exit(player):
            self.last_denied = True
            return False
        self.is_open = True
        self.activated = True
        self.last_denied = False
        return True

    def reset(self) -> None:
        super().reset()
        self.activated = False

    def draw(
        self,
        surface: pygame.Surface,
        offset: Sequence[float] | pygame.Vector2 = (0.0, 0.0),
    ) -> None:
        super().draw(surface, offset)
        draw_rect = self.rect.move(round(offset[0]), round(offset[1]))
        sign = pygame.Rect(0, 0, max(18, draw_rect.width - 10), 12)
        sign.midtop = (draw_rect.centerx, draw_rect.top + 3)
        pygame.draw.rect(surface, (13, 46, 37), sign, border_radius=2)
        pygame.draw.rect(surface, (39, 215, 102), sign, width=2, border_radius=2)


ExitDoor = Exit

__all__ = ["Door", "Exit", "ExitDoor"]
