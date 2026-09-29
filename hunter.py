"""Hunter-X pursuit unit for the Robot Lab Escape expansion.

Hunter-X deliberately reuses :class:`enemy.SecurityBot` navigation so it can
be dropped into the same update loop.  The extra lifecycle is kept orthogonal
to the security state machine: a hunter may be dormant or EMP-disabled while
its underlying patrol/chase state remains available to game code.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any

import pygame

import settings
from enemy import EnemyState, SecurityBot


DEFAULT_TILE_SIZE = int(getattr(settings, "TILE_SIZE", 48))
DEFAULT_PATROL_SPEED = float(getattr(settings, "ENEMY_PATROL_SPEED", 105.0))
DEFAULT_CHASE_SPEED = float(getattr(settings, "ENEMY_CHASE_SPEED", 165.0))
DEFAULT_DETECTION_RANGE = float(
    getattr(settings, "ENEMY_DETECTION_RANGE", DEFAULT_TILE_SIZE * 5.0)
)

# The fallbacks intentionally remain stronger than the standard security bot.
DEFAULT_HUNTER_PATROL_SPEED = float(
    getattr(settings, "HUNTER_PATROL_SPEED", DEFAULT_PATROL_SPEED * 1.2)
)
DEFAULT_HUNTER_CHASE_SPEED = float(
    getattr(settings, "HUNTER_CHASE_SPEED", DEFAULT_CHASE_SPEED * 1.25)
)
DEFAULT_HUNTER_DETECTION_RANGE = float(
    getattr(settings, "HUNTER_DETECTION_RANGE", DEFAULT_DETECTION_RANGE * 1.4)
)
DEFAULT_DISABLE_DURATION = float(getattr(settings, "EMP_DISABLE_SECONDS", 5.0))
DEFAULT_HUNTER_SIZE = (40, 32)


def _position_of(value: object) -> pygame.Vector2:
    """Coerce a world position, sprite, or rectangle to a center vector."""

    if isinstance(value, pygame.Rect):
        return pygame.Vector2(value.center)
    rect = getattr(value, "rect", None)
    if isinstance(rect, pygame.Rect):
        return pygame.Vector2(rect.center)
    position = getattr(value, "position", getattr(value, "pos", value))
    return pygame.Vector2(position)  # type: ignore[arg-type]


class HunterX(SecurityBot):
    """A stronger security bot that begins dormant and supports EMP stuns.

    ``state`` remains an :class:`enemy.EnemyState`, which lets existing game
    code compare it with ``CHASE``/``SEARCH`` as usual.  ``state_name`` reports
    the higher-priority lifecycle states ``DORMANT`` and ``DISABLED`` when
    appropriate.
    """

    DORMANT = "DORMANT"
    DISABLED = "DISABLED"

    def __init__(
        self,
        start: Sequence[float] | pygame.Vector2,
        waypoints: Iterable[Sequence[float] | pygame.Vector2] | None = None,
        *,
        active: bool = False,
        tile_size: int = DEFAULT_TILE_SIZE,
        size: int | tuple[int, int] = DEFAULT_HUNTER_SIZE,
        patrol_speed: float = DEFAULT_HUNTER_PATROL_SPEED,
        chase_speed: float = DEFAULT_HUNTER_CHASE_SPEED,
        detection_range: float = DEFAULT_HUNTER_DETECTION_RANGE,
        disable_duration: float = DEFAULT_DISABLE_DURATION,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            start,
            waypoints,
            tile_size=tile_size,
            size=size,
            patrol_speed=patrol_speed,
            chase_speed=chase_speed,
            detection_range=detection_range,
            **kwargs,
        )
        self._configured_active = bool(active)
        self.active = bool(active)
        self.disable_duration = max(0.0, float(disable_duration))
        self.disabled_remaining = 0.0

    @staticmethod
    def _make_image(size: tuple[int, int]) -> pygame.Surface:
        """Create a distinct fallback sprite without requiring art assets."""

        surface = pygame.Surface(size, pygame.SRCALPHA)
        body = surface.get_rect().inflate(-4, -4)
        pygame.draw.rect(surface, (67, 73, 82), body, border_radius=6)
        pygame.draw.rect(surface, (18, 22, 28), body, width=2, border_radius=6)
        armor = body.inflate(-8, -8)
        pygame.draw.rect(surface, (105, 36, 44), armor, border_radius=4)
        visor = pygame.Rect(0, 0, max(12, size[0] // 2), max(5, size[1] // 5))
        visor.midtop = (size[0] // 2, max(4, size[1] // 6))
        pygame.draw.rect(surface, (25, 8, 12), visor, border_radius=2)
        pygame.draw.circle(surface, (255, 96, 72), visor.center, max(2, visor.height // 3))
        return surface

    @property
    def is_disabled(self) -> bool:
        return self.disabled_remaining > 0.0

    @property
    def disabled(self) -> bool:
        """Convenient boolean alias for UI and effect code."""

        return self.is_disabled

    @property
    def dormant(self) -> bool:
        return not self.active

    @property
    def state_name(self) -> str:
        if self.is_disabled:
            return self.DISABLED
        if not self.active:
            return self.DORMANT
        return self.state.value

    @property
    def security_state(self) -> str:
        return self.state_name

    @property
    def alerted(self) -> bool:
        return self.active and not self.is_disabled and super().alerted

    def _halt(self, *, discard_path: bool = False) -> None:
        self.velocity.update(0.0, 0.0)
        if discard_path:
            self._path_world.clear()
            self._path_target_tile = None
            self._repath_remaining = 0.0

    def activate(self, last_seen: object | None = None) -> bool:
        """Wake Hunter-X, optionally directing it toward a known target.

        Returns ``True`` only when the unit changed from dormant to active.
        A supplied ``last_seen`` may be a position, rect, or sprite-like object.
        """

        changed = not self.active
        self.active = True
        self._halt(discard_path=True)
        if last_seen is None:
            self.last_seen_position = None
            self.set_state(EnemyState.PATROL)
        else:
            self.last_seen_position = _position_of(last_seen)
            self.set_state(EnemyState.CHASE)
        return changed

    def deactivate(self) -> bool:
        """Return Hunter-X to a harmless dormant state."""

        changed = self.active
        self.active = False
        self.last_seen_position = None
        self.set_state(EnemyState.PATROL)
        self._halt(discard_path=True)
        return changed

    def disable(self, duration: float | None = None) -> bool:
        """EMP-disable the unit without shortening an existing stun.

        ``None`` uses the configured default duration.  Returns whether the
        unit is disabled after the call.
        """

        seconds = self.disable_duration if duration is None else max(0.0, float(duration))
        self.disabled_remaining = max(self.disabled_remaining, seconds)
        if self.is_disabled:
            self._halt(discard_path=True)
        return self.is_disabled

    stun = disable

    def sees_player(
        self,
        player: object,
        blockers: Iterable[object] = (),
        los_test: Callable[..., bool] | None = None,
    ) -> bool:
        if not self.active or self.is_disabled:
            return False
        return super().sees_player(player, blockers, los_test)

    def update(
        self,
        dt: float,
        player: object,
        blockers: Iterable[object] = (),
        *,
        tile_map: object | None = None,
        opened_doors: Iterable[object] = (),
        los_test: Callable[..., bool] | None = None,
        pathfinder: Callable[..., Sequence[Sequence[int]]] | None = None,
    ) -> None:
        """Advance the unit using the standard bot-compatible update API."""

        seconds = max(0.0, float(dt))
        if self.is_disabled:
            self.disabled_remaining = max(0.0, self.disabled_remaining - seconds)
            self._halt()
            return
        if not self.active:
            self._halt()
            return
        super().update(
            seconds,
            player,
            blockers,
            tile_map=tile_map,
            opened_doors=opened_doors,
            los_test=los_test,
            pathfinder=pathfinder,
        )

    def touching_player(self, player: object) -> bool:
        if not self.active or self.is_disabled:
            return False
        return super().touching_player(player)

    has_caught = touching_player

    def reset(
        self,
        start: Sequence[float] | pygame.Vector2 | None = None,
        *,
        active: bool | None = None,
    ) -> None:
        """Restore position, AI, stun timer, and configured activity."""

        super().reset(start)
        self.active = self._configured_active if active is None else bool(active)
        self.disabled_remaining = 0.0


Hunter = HunterX

__all__ = ["Hunter", "HunterX"]
