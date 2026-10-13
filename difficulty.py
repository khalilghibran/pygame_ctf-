"""Player-selectable gameplay profiles for the five-chapter campaign."""

from __future__ import annotations

from dataclasses import dataclass

import settings


@dataclass(frozen=True, slots=True)
class DifficultyProfile:
    """Values used when a mission is created or its systems are activated."""

    name: str
    player_speed: float
    battery_drain: float
    dash_drain: float
    battery_pickup: float
    enemy_patrol_speed: float
    enemy_chase_speed: float
    enemy_detection_range: float
    hunter_patrol_speed: float
    hunter_chase_speed: float
    hunter_detection_range: float
    boss_patrol_speed: float
    boss_chase_speed: float
    boss_detection_range: float
    boss_stun_seconds: float
    cctv_detection_seconds: float
    hack_length: int
    hack_reveal_seconds: float
    hack_attempts: int
    interaction_padding: int
    contact_battery_penalty: float
    contact_grace_seconds: float
    auto_collect: bool


EXPLORER = DifficultyProfile(
    name="EXPLORER",
    player_speed=240.0,
    battery_drain=0.55,
    dash_drain=2.0,
    battery_pickup=50.0,
    enemy_patrol_speed=85.0,
    enemy_chase_speed=125.0,
    enemy_detection_range=4.0 * settings.TILE_SIZE,
    hunter_patrol_speed=100.0,
    hunter_chase_speed=150.0,
    hunter_detection_range=5.5 * settings.TILE_SIZE,
    boss_patrol_speed=95.0,
    boss_chase_speed=145.0,
    boss_detection_range=5.0 * settings.TILE_SIZE,
    boss_stun_seconds=2.1,
    cctv_detection_seconds=1.5,
    hack_length=3,
    hack_reveal_seconds=3.5,
    hack_attempts=5,
    interaction_padding=30,
    contact_battery_penalty=20.0,
    contact_grace_seconds=2.5,
    auto_collect=True,
)

CLASSIC = DifficultyProfile(
    name="CLASSIC",
    player_speed=settings.PLAYER_SPEED,
    battery_drain=settings.BATTERY_DRAIN_PER_SECOND,
    dash_drain=settings.DASH_BATTERY_DRAIN_PER_SECOND,
    battery_pickup=settings.BATTERY_PICKUP_AMOUNT,
    enemy_patrol_speed=settings.ENEMY_PATROL_SPEED,
    enemy_chase_speed=settings.ENEMY_CHASE_SPEED,
    enemy_detection_range=settings.ENEMY_DETECTION_RANGE,
    hunter_patrol_speed=settings.HUNTER_PATROL_SPEED,
    hunter_chase_speed=settings.HUNTER_CHASE_SPEED,
    hunter_detection_range=settings.HUNTER_DETECTION_RANGE,
    boss_patrol_speed=settings.BOSS_PATROL_SPEED,
    boss_chase_speed=settings.BOSS_CHASE_SPEED,
    boss_detection_range=settings.BOSS_DETECTION_RANGE,
    boss_stun_seconds=settings.BOSS_STUN_SECONDS,
    cctv_detection_seconds=settings.CCTV_DETECTION_SECONDS,
    hack_length=settings.HACK_SEQUENCE_LENGTH,
    hack_reveal_seconds=settings.HACK_REVEAL_SECONDS,
    hack_attempts=settings.HACK_MAX_ATTEMPTS,
    interaction_padding=20,
    contact_battery_penalty=0.0,
    contact_grace_seconds=0.0,
    auto_collect=False,
)


__all__ = ["DifficultyProfile", "EXPLORER", "CLASSIC"]
