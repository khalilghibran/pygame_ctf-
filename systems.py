"""Expansion gameplay systems: hacking, CCTV surveillance, and EMP pickups."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from enum import Enum
from typing import Any

import pygame

try:
    import settings as _settings
except ImportError:  # pragma: no cover
    _settings = None


def _setting(name: str, default: Any) -> Any:
    return getattr(_settings, name, default) if _settings is not None else default


TILE_SIZE = int(_setting("TILE_SIZE", 48))
HACK_LENGTH = int(_setting("HACK_SEQUENCE_LENGTH", 4))
HACK_REVEAL = float(_setting("HACK_REVEAL_SECONDS", 1.8))
HACK_ATTEMPTS = int(_setting("HACK_MAX_ATTEMPTS", 3))
CCTV_RANGE = float(_setting("CCTV_RANGE", TILE_SIZE * 5.5))
CCTV_FOV = float(_setting("CCTV_FOV_DEGREES", 62.0))
CCTV_SWEEP = float(_setting("CCTV_SWEEP_DEGREES", 55.0))
CCTV_SPEED = float(_setting("CCTV_SWEEP_SPEED", 48.0))
CCTV_DETECTION = float(_setting("CCTV_DETECTION_SECONDS", 0.85))


def _world_center(tile: Sequence[int], tile_size: int) -> tuple[float, float]:
    return (tile[0] + 0.5) * tile_size, (tile[1] + 0.5) * tile_size


class HackingState(str, Enum):
    REVEAL = "REVEAL"
    INPUT = "INPUT"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class HackingPuzzle:
    """A deterministic-friendly memory sequence challenge using symbols 1-4."""

    def __init__(
        self,
        sequence: Sequence[str | int] | None = None,
        *,
        length: int = HACK_LENGTH,
        symbols: Sequence[str] = ("1", "2", "3", "4"),
        reveal_duration: float = HACK_REVEAL,
        max_attempts: int = HACK_ATTEMPTS,
        rng: random.Random | None = None,
    ) -> None:
        self.length = max(1, int(length))
        self.symbols = tuple(map(str, symbols))
        if not self.symbols:
            raise ValueError("symbols must not be empty")
        self.reveal_duration = max(0.0, float(reveal_duration))
        self.max_attempts = max(1, int(max_attempts))
        self._rng = rng or random.Random()
        self._provided_sequence = tuple(map(str, sequence)) if sequence is not None else None
        if self._provided_sequence is not None:
            self.length = len(self._provided_sequence)
        self.sequence: tuple[str, ...] = ()
        self.input_buffer: list[str] = []
        self.state = HackingState.REVEAL
        self.reveal_remaining = self.reveal_duration
        self.attempts_remaining = self.max_attempts
        self.last_submission_correct: bool | None = None
        self.reset(sequence=self._provided_sequence)

    @property
    def phase(self) -> HackingState:
        return self.state

    @property
    def entered(self) -> tuple[str, ...]:
        return tuple(self.input_buffer)

    @property
    def succeeded(self) -> bool:
        return self.state is HackingState.SUCCESS

    @property
    def failed(self) -> bool:
        return self.state is HackingState.FAILURE

    @property
    def accepting_input(self) -> bool:
        return self.state is HackingState.INPUT

    def _new_sequence(self) -> tuple[str, ...]:
        return tuple(self._rng.choice(self.symbols) for _ in range(self.length))

    def update(self, dt: float) -> HackingState:
        if self.state is HackingState.REVEAL:
            self.reveal_remaining = max(0.0, self.reveal_remaining - max(0.0, float(dt)))
            if self.reveal_remaining <= 0.0:
                self.state = HackingState.INPUT
        return self.state

    def enter_symbol(self, symbol: str | int) -> bool:
        value = str(symbol)
        if not self.accepting_input or value not in self.symbols:
            return False
        if len(self.input_buffer) >= len(self.sequence):
            return False
        self.input_buffer.append(value)
        return True

    def backspace(self) -> bool:
        if not self.accepting_input or not self.input_buffer:
            return False
        self.input_buffer.pop()
        return True

    def submit(self, value: Sequence[str | int] | str | int | None = None) -> bool | None:
        """Enter a symbol/sequence, or validate the current buffer with ``None``."""

        if value is not None:
            if isinstance(value, (str, int)):
                text = str(value)
                if len(text) == 1:
                    self.enter_symbol(text)
                    return None
                values = tuple(text)
            else:
                values = tuple(map(str, value))
            if self.accepting_input:
                self.input_buffer = [v for v in values if v in self.symbols][
                    : len(self.sequence)
                ]
            return None

        if not self.accepting_input or len(self.input_buffer) != len(self.sequence):
            return False
        correct = tuple(self.input_buffer) == self.sequence
        self.last_submission_correct = correct
        if correct:
            self.state = HackingState.SUCCESS
            return True

        self.attempts_remaining -= 1
        self.input_buffer.clear()
        if self.attempts_remaining <= 0:
            self.state = HackingState.FAILURE
        else:
            self.state = HackingState.REVEAL
            self.reveal_remaining = self.reveal_duration
        return False

    def reset(self, sequence: Sequence[str | int] | None = None) -> None:
        if sequence is not None:
            self._provided_sequence = tuple(map(str, sequence))
            self.length = len(self._provided_sequence)
        self.sequence = self._provided_sequence or self._new_sequence()
        self.input_buffer.clear()
        self.state = HackingState.REVEAL
        self.reveal_remaining = self.reveal_duration
        self.attempts_remaining = self.max_attempts
        self.last_submission_correct = None


class Terminal:
    """A key-authorized security terminal that owns its current puzzle."""

    kind = "terminal"
    blocks = False
    blocks_los = False
    solid = False

    def __init__(
        self,
        position: Sequence[float],
        *,
        size: int | tuple[int, int] = 34,
        required_key: str | None = "blue",
    ) -> None:
        dimensions = (size, size) if isinstance(size, int) else size
        self.position = pygame.Vector2(position)
        self.rect = pygame.Rect(0, 0, *dimensions)
        self.rect.center = tuple(map(round, self.position))
        self.required_key = required_key.casefold() if required_key else None
        self.hacked = False
        self.active = True
        self.puzzle: HackingPuzzle | None = None

    @classmethod
    def from_tile(
        cls, tile: Sequence[int], *, tile_size: int = TILE_SIZE, **kwargs: Any
    ) -> "Terminal":
        return cls(_world_center(tile, tile_size), **kwargs)

    @property
    def locked(self) -> bool:
        return not self.hacked

    def authorized(self, player: object | None) -> bool:
        if self.required_key is None:
            return True
        has_keycard = getattr(player, "has_keycard", None)
        return bool(callable(has_keycard) and has_keycard(self.required_key))

    def can_interact(self, player: object, padding: int = 20) -> bool:
        player_rect = getattr(player, "rect", None)
        return (
            self.active
            and isinstance(player_rect, pygame.Rect)
            and player_rect.inflate(padding * 2, padding * 2).colliderect(self.rect)
        )

    def begin_hack(
        self,
        player: object | None = None,
        *,
        sequence: Sequence[str | int] | None = None,
        rng: random.Random | None = None,
    ) -> HackingPuzzle | None:
        if self.hacked or not self.authorized(player):
            return None
        self.puzzle = HackingPuzzle(sequence, rng=rng)
        return self.puzzle

    interact = begin_hack

    def mark_hacked(self) -> None:
        self.hacked = True
        self.puzzle = None

    def reset(self) -> None:
        self.hacked = False
        self.active = True
        self.puzzle = None


class CCTV:
    """A sweeping camera with field-of-view, LOS, and detection buildup."""

    kind = "camera"
    blocks = False
    blocks_los = False
    solid = False

    def __init__(
        self,
        position: Sequence[float],
        *,
        tile_size: int = TILE_SIZE,
        base_angle: float = 90.0,
        range_pixels: float = CCTV_RANGE,
        fov_degrees: float = CCTV_FOV,
        sweep_degrees: float = CCTV_SWEEP,
        sweep_speed: float = CCTV_SPEED,
        detection_seconds: float = CCTV_DETECTION,
    ) -> None:
        self.position = pygame.Vector2(position)
        self.rect = pygame.Rect(0, 0, max(20, tile_size // 2), max(20, tile_size // 2))
        self.rect.center = tuple(map(round, self.position))
        self.tile_size = tile_size
        self.base_angle = float(base_angle)
        self.angle = float(base_angle)
        self.range = max(0.0, float(range_pixels))
        self.fov_degrees = max(0.0, min(360.0, float(fov_degrees)))
        self.sweep_degrees = max(0.0, float(sweep_degrees))
        self.sweep_speed = max(0.0, float(sweep_speed))
        self.sweep_direction = 1.0
        self.detection_seconds = max(0.01, float(detection_seconds))
        self.detection_progress = 0.0
        self.disabled_remaining = 0.0
        self.permanently_disabled = False
        self._detection_latched = False

    @classmethod
    def from_tile(
        cls, tile: Sequence[int], *, tile_size: int = TILE_SIZE, **kwargs: Any
    ) -> "CCTV":
        return cls(_world_center(tile, tile_size), tile_size=tile_size, **kwargs)

    @property
    def disabled(self) -> bool:
        return self.permanently_disabled or self.disabled_remaining > 0.0

    @property
    def detection_ratio(self) -> float:
        return min(1.0, self.detection_progress / self.detection_seconds)

    @property
    def direction(self) -> str:
        vector = pygame.Vector2(1, 0).rotate(self.angle)
        if abs(vector.x) > abs(vector.y):
            return "right" if vector.x > 0 else "left"
        return "down" if vector.y > 0 else "up"

    @property
    def state_name(self) -> str:
        if self.disabled:
            return "OFFLINE"
        return "DETECTED" if self._detection_latched else "SCANNING"

    def disable(self, duration: float) -> None:
        self.disabled_remaining = max(self.disabled_remaining, max(0.0, float(duration)))
        self.detection_progress = 0.0
        self._detection_latched = False

    def disable_permanently(self) -> None:
        self.permanently_disabled = True
        self.detection_progress = 0.0
        self._detection_latched = False

    def can_see(
        self,
        target: Sequence[float] | pygame.Vector2,
        los_test: Callable[..., bool] | None = None,
    ) -> bool:
        if self.disabled:
            return False
        target_position = pygame.Vector2(target)
        offset = target_position - self.position
        if offset.length_squared() > self.range**2 or offset.length_squared() <= 1e-9:
            return False
        target_angle = math.degrees(math.atan2(offset.y, offset.x))
        difference = (target_angle - self.angle + 180.0) % 360.0 - 180.0
        if abs(difference) > self.fov_degrees / 2.0:
            return False
        if los_test is not None:
            try:
                return bool(los_test(self.position, target_position, ()))
            except TypeError:
                return bool(los_test(self.position, target_position))
        return True

    def update(
        self,
        dt: float,
        target: Sequence[float] | pygame.Vector2 | None = None,
        los_test: Callable[..., bool] | None = None,
    ) -> bool:
        seconds = max(0.0, min(float(dt), 0.1))
        if self.disabled_remaining > 0.0:
            self.disabled_remaining = max(0.0, self.disabled_remaining - seconds)
        if self.disabled:
            self.detection_progress = 0.0
            self._detection_latched = False
            return False

        self.angle += self.sweep_speed * self.sweep_direction * seconds
        lower = self.base_angle - self.sweep_degrees
        upper = self.base_angle + self.sweep_degrees
        if self.angle >= upper:
            self.angle = upper
            self.sweep_direction = -1.0
        elif self.angle <= lower:
            self.angle = lower
            self.sweep_direction = 1.0

        visible = target is not None and self.can_see(target, los_test)
        if visible:
            self.detection_progress = min(
                self.detection_seconds, self.detection_progress + seconds
            )
        else:
            self.detection_progress = max(0.0, self.detection_progress - seconds * 1.5)
            if self.detection_progress < self.detection_seconds * 0.25:
                self._detection_latched = False

        if self.detection_progress >= self.detection_seconds and not self._detection_latched:
            self._detection_latched = True
            return True
        return False

    def reset(self) -> None:
        self.angle = self.base_angle
        self.sweep_direction = 1.0
        self.detection_progress = 0.0
        self.disabled_remaining = 0.0
        self.permanently_disabled = False
        self._detection_latched = False


class EMPCharge:
    """Pickup that grants a player one bounded EMP charge."""

    kind = "emp"
    blocks = False
    blocks_los = False
    solid = False

    def __init__(self, position: Sequence[float], *, amount: int = 1) -> None:
        self.position = pygame.Vector2(position)
        self.rect = pygame.Rect(0, 0, 24, 24)
        self.rect.center = tuple(map(round, self.position))
        self.amount = max(1, int(amount))
        self.active = True

    @classmethod
    def from_tile(
        cls, tile: Sequence[int], *, tile_size: int = TILE_SIZE, **kwargs: Any
    ) -> "EMPCharge":
        return cls(_world_center(tile, tile_size), **kwargs)

    def can_interact(self, player: object, padding: int = 20) -> bool:
        player_rect = getattr(player, "rect", None)
        return (
            self.active
            and isinstance(player_rect, pygame.Rect)
            and player_rect.inflate(padding * 2, padding * 2).colliderect(self.rect)
        )

    def interact(self, player: object) -> bool:
        if not self.active:
            return False
        add = getattr(player, "add_emp_charge", None)
        if not callable(add) or int(add(self.amount)) <= 0:
            return False
        self.active = False
        return True

    collect = interact

    def reset(self) -> None:
        self.active = True


__all__ = ["CCTV", "EMPCharge", "HackingPuzzle", "HackingState", "Terminal"]
