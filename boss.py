"""Final-chapter WARDEN PRIME boss behavior."""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterable, Sequence

import pygame

import settings
from enemy import SecurityBot


class BossHit(str, Enum):
    """Result of exposing WARDEN PRIME to an EMP pulse."""

    SHIELDED = "SHIELDED"
    COOLDOWN = "COOLDOWN"
    DAMAGED = "DAMAGED"
    DEFEATED = "DEFEATED"
    ALREADY_DEFEATED = "ALREADY_DEFEATED"


class WardenPrime(SecurityBot):
    """Large pursuit unit whose shield must be disabled before EMP damage."""

    kind = "boss"

    def __init__(
        self,
        start: Sequence[float] | pygame.Vector2,
        waypoints: Iterable[Sequence[float] | pygame.Vector2] | None = None,
        *,
        max_health: int = settings.BOSS_MAX_HEALTH,
        hit_cooldown: float = settings.BOSS_HIT_COOLDOWN_SECONDS,
        stun_seconds: float = settings.BOSS_STUN_SECONDS,
        **kwargs: Any,
    ) -> None:
        super().__init__(start, waypoints, **kwargs)
        self.max_health = max(1, int(max_health))
        self.health = self.max_health
        self.hit_cooldown = max(0.0, float(hit_cooldown))
        self.stun_seconds = max(0.0, float(stun_seconds))
        self.damage_cooldown_remaining = 0.0
        self.defeated = False

    @property
    def state_name(self) -> str:
        if self.defeated:
            return "DEFEATED"
        if self.disabled:
            return "STUNNED"
        return super().state_name

    @property
    def health_ratio(self) -> float:
        return self.health / self.max_health

    @property
    def ready_for_emp(self) -> bool:
        return not self.defeated and self.damage_cooldown_remaining <= 0.0

    def receive_emp(self, *, shield_down: bool) -> BossHit:
        """Resolve an EMP pulse without letting rapid key presses waste charges."""

        if self.defeated:
            return BossHit.ALREADY_DEFEATED
        if not shield_down:
            self.disable(min(1.0, self.stun_seconds))
            return BossHit.SHIELDED
        if not self.ready_for_emp:
            return BossHit.COOLDOWN

        self.health = max(0, self.health - 1)
        self.damage_cooldown_remaining = self.hit_cooldown
        if self.health <= 0:
            self.defeated = True
            self.velocity.update(0.0, 0.0)
            self.disabled_remaining = 0.0
            return BossHit.DEFEATED

        self.disable(self.stun_seconds)
        return BossHit.DAMAGED

    def update(self, dt: float, *args: Any, **kwargs: Any) -> None:
        seconds = max(0.0, min(float(dt), 0.1))
        self.damage_cooldown_remaining = max(
            0.0, self.damage_cooldown_remaining - seconds
        )
        if self.defeated:
            self.velocity.update(0.0, 0.0)
            return
        super().update(dt, *args, **kwargs)

    def sees_player(self, *args: Any, **kwargs: Any) -> bool:
        return not self.defeated and super().sees_player(*args, **kwargs)

    def touching_player(self, player: object) -> bool:
        return not self.defeated and super().touching_player(player)

    def alert_to(self, position: Sequence[float] | pygame.Vector2) -> bool:
        if self.defeated:
            return False
        return super().alert_to(position)

    def reset(self, start: Sequence[float] | pygame.Vector2 | None = None) -> None:
        super().reset(start)
        self.health = self.max_health
        self.damage_cooldown_remaining = 0.0
        self.defeated = False


__all__ = ["BossHit", "WardenPrime"]
