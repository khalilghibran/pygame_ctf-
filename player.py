"""Player entity for Robot Lab Escape.

The class deliberately keeps input handling outside the entity: callers pass a
movement vector to :meth:`Player.update`.  That makes movement deterministic,
easy to test, and usable with either keyboard or controller input.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import pygame

try:  # Keep the entity usable while the rest of the project is being built.
    import settings as _settings
except ImportError:  # pragma: no cover - useful when this module is reused alone
    _settings = None


def _setting(name: str, default: Any) -> Any:
    return getattr(_settings, name, default) if _settings is not None else default


DEFAULT_SPEED = float(_setting("PLAYER_SPEED", 180.0))
DEFAULT_MAX_BATTERY = float(_setting("BATTERY_MAX", 100.0))
DEFAULT_START_BATTERY = float(_setting("BATTERY_START", DEFAULT_MAX_BATTERY))
DEFAULT_BATTERY_DRAIN = float(
    _setting(
        "BATTERY_DRAIN_RATE",
        _setting("BATTERY_DRAIN_PER_SECOND", 0.65),
    )
)
DEFAULT_TILE_SIZE = int(_setting("TILE_SIZE", 32))
DEFAULT_HITBOX_SIZE = int(_setting("PLAYER_HITBOX_SIZE", 28))
DEFAULT_MAX_EMP_CHARGES = int(_setting("EMP_MAX_CHARGES", 3))
PLAYER_COLOR = pygame.Color(_setting("PLAYER_CYAN", "#28D7FF"))


def _coerce_rect(blocker: object) -> pygame.Rect | None:
    """Return a blocker rectangle, ignoring explicitly non-solid objects."""

    if hasattr(blocker, "blocks") and not bool(getattr(blocker, "blocks")):
        return None
    if hasattr(blocker, "solid") and not bool(getattr(blocker, "solid")):
        return None
    if isinstance(blocker, pygame.Rect):
        return blocker
    rect = getattr(blocker, "rect", None)
    return rect if isinstance(rect, pygame.Rect) else None


class Player(pygame.sprite.Sprite):
    """A continuously positioned player with a rectangular collision hitbox.

    ``start`` is interpreted as a world-space center.  Use :meth:`from_tile`
    when constructing directly from an ASCII-map tile coordinate.
    """

    def __init__(
        self,
        start: Sequence[float] | pygame.Vector2,
        *,
        size: int | tuple[int, int] = DEFAULT_HITBOX_SIZE,
        speed: float = DEFAULT_SPEED,
        max_battery: float = DEFAULT_MAX_BATTERY,
        starting_battery: float = DEFAULT_START_BATTERY,
        battery_drain_rate: float = DEFAULT_BATTERY_DRAIN,
        max_emp_charges: int = DEFAULT_MAX_EMP_CHARGES,
    ) -> None:
        super().__init__()
        width, height = (size, size) if isinstance(size, int) else size
        self.image = self._make_image((int(width), int(height)))
        self.rect = self.image.get_rect(center=(round(start[0]), round(start[1])))

        self.start_position = pygame.Vector2(start)
        self.position = pygame.Vector2(start)
        self.pos = self.position  # Familiar alias used by many Pygame projects.
        self.speed = float(speed)
        self.max_battery = max(0.0, float(max_battery))
        self.starting_battery = max(0.0, min(self.max_battery, float(starting_battery)))
        self.battery_drain_rate = max(0.0, float(battery_drain_rate))
        self.battery = self.starting_battery
        self.keycards: set[str] = set()
        self.max_emp_charges = max(0, int(max_emp_charges))
        self.emp_charges = 0
        self.facing = "down"
        self.velocity = pygame.Vector2()
        self.is_moving = False

    @classmethod
    def from_tile(
        cls,
        tile: Sequence[int],
        *,
        tile_size: int = DEFAULT_TILE_SIZE,
        **kwargs: Any,
    ) -> "Player":
        """Build a player centered in ``tile``."""

        center = ((tile[0] + 0.5) * tile_size, (tile[1] + 0.5) * tile_size)
        return cls(center, **kwargs)

    @staticmethod
    def _make_image(size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        body = surface.get_rect().inflate(-4, -3)
        pygame.draw.rect(surface, (220, 233, 240), body, border_radius=7)
        pygame.draw.rect(surface, (47, 72, 91), body, width=2, border_radius=7)
        eye = pygame.Rect(0, 0, max(7, size[0] // 2), max(4, size[1] // 5))
        eye.midtop = (size[0] // 2, max(4, size[1] // 5))
        pygame.draw.rect(surface, (16, 34, 48), eye, border_radius=3)
        pygame.draw.circle(surface, PLAYER_COLOR, eye.center, max(2, eye.height // 3))
        return surface

    @property
    def battery_ratio(self) -> float:
        """Battery charge as a clamped value in the inclusive range 0..1."""

        if self.max_battery <= 0:
            return 0.0
        return max(0.0, min(1.0, self.battery / self.max_battery))

    @property
    def is_powered(self) -> bool:
        return self.battery > 0.0

    @property
    def inventory(self) -> set[str]:
        """Alias for the owned keycard colors."""

        return self.keycards

    def has_keycard(self, color: str = "blue") -> bool:
        return color.casefold() in self.keycards

    def give_keycard(self, color: str = "blue") -> bool:
        """Add a keycard and return whether it was newly acquired."""

        normalized = color.casefold()
        was_new = normalized not in self.keycards
        self.keycards.add(normalized)
        return was_new

    add_keycard = give_keycard

    def add_emp_charge(self, amount: int = 1) -> int:
        """Store EMP charges and return the number actually accepted."""

        before = self.emp_charges
        self.emp_charges = min(
            self.max_emp_charges, self.emp_charges + max(0, int(amount))
        )
        return self.emp_charges - before

    def use_emp_charge(self) -> bool:
        """Consume one EMP charge when available."""

        if self.emp_charges <= 0:
            return False
        self.emp_charges -= 1
        return True

    def drain_battery(self, dt: float, rate: float | None = None) -> bool:
        """Drain charge for ``dt`` seconds and return ``True`` if depleted."""

        drain_rate = self.battery_drain_rate if rate is None else max(0.0, float(rate))
        self.battery = max(0.0, self.battery - drain_rate * max(0.0, float(dt)))
        return self.battery <= 0.0

    def restore_battery(self, amount: float) -> float:
        """Restore charge, returning the actual amount accepted."""

        before = self.battery
        self.battery = min(self.max_battery, self.battery + max(0.0, float(amount)))
        return self.battery - before

    def update(
        self,
        dt: float,
        movement: Sequence[float] | pygame.Vector2 = (0.0, 0.0),
        blockers: Iterable[object] = (),
    ) -> None:
        """Move for one frame.

        Diagonal input is normalized, position is retained at floating-point
        precision, and collision is resolved one axis at a time so the player
        slides naturally along walls.
        """

        direction = pygame.Vector2(movement)
        if direction.length_squared() > 1.0:
            direction.normalize_ip()
        self.velocity = direction * self.speed
        self.is_moving = direction.length_squared() > 0.0
        if self.is_moving:
            if abs(direction.x) > abs(direction.y):
                self.facing = "right" if direction.x > 0 else "left"
            else:
                self.facing = "down" if direction.y > 0 else "up"

        seconds = max(0.0, min(float(dt), 0.1))
        solid_rects = tuple(
            rect for blocker in blockers if (rect := _coerce_rect(blocker)) is not None
        )
        self._move_axis(self.velocity.x * seconds, 0.0, solid_rects)
        self._move_axis(0.0, self.velocity.y * seconds, solid_rects)

    def _move_axis(
        self,
        dx: float,
        dy: float,
        blockers: Sequence[pygame.Rect],
    ) -> bool:
        """Move one axis, returning whether a collision was resolved."""

        if dx == 0.0 and dy == 0.0:
            return False
        self.position.x += dx
        self.position.y += dy
        self.rect.center = (round(self.position.x), round(self.position.y))

        collided = False
        for obstacle in blockers:
            if not self.rect.colliderect(obstacle):
                continue
            collided = True
            if dx > 0:
                self.rect.right = obstacle.left
            elif dx < 0:
                self.rect.left = obstacle.right
            elif dy > 0:
                self.rect.bottom = obstacle.top
            elif dy < 0:
                self.rect.top = obstacle.bottom
            self.position.update(self.rect.center)
        return collided

    def interaction_rect(self, padding: int = 18) -> pygame.Rect:
        """Return a proximity rectangle suitable for ``E`` interactions."""

        return self.rect.inflate(padding * 2, padding * 2)

    def reset(self, start: Sequence[float] | pygame.Vector2 | None = None) -> None:
        """Restore initial position, inventory, battery, and movement state."""

        if start is not None:
            self.start_position.update(start)
        self.position.update(self.start_position)
        self.rect.center = (round(self.position.x), round(self.position.y))
        self.velocity.update(0.0, 0.0)
        self.keycards.clear()
        self.emp_charges = 0
        self.battery = self.starting_battery
        self.facing = "down"
        self.is_moving = False

    def draw(
        self,
        surface: pygame.Surface,
        offset: Sequence[float] | pygame.Vector2 = (0.0, 0.0),
    ) -> None:
        draw_rect = self.image.get_rect(
            center=(round(self.rect.centerx + offset[0]), round(self.rect.centery + offset[1]))
        )
        surface.blit(self.image, draw_rect)


__all__ = ["Player"]
