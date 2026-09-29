"""Shared configuration for the Robot Lab Escape prototype.

The core modules deliberately keep these values independent of Pygame so they
can be imported by tests and tooling without initializing a display.
"""

from __future__ import annotations

from typing import Final, TypeAlias


Color: TypeAlias = tuple[int, int, int]

# Display and timing -------------------------------------------------------
SCREEN_WIDTH: Final = 1280
SCREEN_HEIGHT: Final = 720
WINDOW_WIDTH: Final = SCREEN_WIDTH
WINDOW_HEIGHT: Final = SCREEN_HEIGHT
WIDTH: Final = SCREEN_WIDTH
HEIGHT: Final = SCREEN_HEIGHT
SCREEN_SIZE: Final = (SCREEN_WIDTH, SCREEN_HEIGHT)
START_FULLSCREEN: Final = True

TILE_SIZE: Final = 48
RENDER_TILE_SIZE: Final = TILE_SIZE
FPS: Final = 60
GAME_TITLE: Final = "Robot Lab Escape"

# Gameplay tuning ---------------------------------------------------------
PLAYER_SPEED: Final = 220.0
PLAYER_HITBOX_SIZE: Final = 30

ENEMY_PATROL_SPEED: Final = 105.0
ENEMY_CHASE_SPEED: Final = 165.0
# Five tiles keeps the opening readable: the bundled player/enemy spawns are
# roughly 6.4 tiles apart and otherwise trigger an immediate chase.
ENEMY_DETECTION_RANGE_TILES: Final = 5.0
ENEMY_DETECTION_RANGE: Final = ENEMY_DETECTION_RANGE_TILES * TILE_SIZE
ENEMY_SEARCH_SECONDS: Final = 3.5
ENEMY_REPATH_SECONDS: Final = 0.35

BATTERY_MAX: Final = 100.0
BATTERY_START: Final = BATTERY_MAX
BATTERY_DRAIN_PER_SECOND: Final = 1.2
BATTERY_PICKUP_AMOUNT: Final = 35.0

# Expansion systems -------------------------------------------------------
DASH_SPEED_MULTIPLIER: Final = 1.7
DASH_BATTERY_DRAIN_PER_SECOND: Final = 4.0

EMP_MAX_CHARGES: Final = 3
EMP_RADIUS_TILES: Final = 5.0
EMP_RADIUS: Final = EMP_RADIUS_TILES * TILE_SIZE
EMP_DISABLE_SECONDS: Final = 5.0
EMP_EFFECT_SECONDS: Final = 0.65

CCTV_RANGE_TILES: Final = 5.5
CCTV_RANGE: Final = CCTV_RANGE_TILES * TILE_SIZE
CCTV_FOV_DEGREES: Final = 62.0
CCTV_SWEEP_DEGREES: Final = 55.0
CCTV_SWEEP_SPEED: Final = 48.0
CCTV_DETECTION_SECONDS: Final = 0.85

HACK_SEQUENCE_LENGTH: Final = 4
HACK_REVEAL_SECONDS: Final = 1.8
HACK_MAX_ATTEMPTS: Final = 3

ALARM_MAX_LEVEL: Final = 3
ALARM_HUNTER_LEVEL: Final = 2

HUNTER_PATROL_SPEED: Final = 125.0
HUNTER_CHASE_SPEED: Final = 205.0
HUNTER_DETECTION_RANGE_TILES: Final = 7.0
HUNTER_DETECTION_RANGE: Final = HUNTER_DETECTION_RANGE_TILES * TILE_SIZE

OBJECTIVE_TEXT: Final = "Find the blue keycard and reach the exit."

# Palette -----------------------------------------------------------------
BACKGROUND_NAVY: Final[Color] = (10, 22, 36)
STEEL_GRAY: Final[Color] = (70, 88, 107)
FLOOR_DARK: Final[Color] = (20, 35, 50)
WALL_DARK: Final[Color] = (38, 55, 72)
WALL_EDGE: Final[Color] = (91, 118, 139)
PLAYER_CYAN: Final[Color] = (40, 215, 255)
SECURITY_RED: Final[Color] = (255, 59, 59)
EXIT_GREEN: Final[Color] = (39, 215, 102)
WARNING_YELLOW: Final[Color] = (248, 196, 49)
KEYCARD_BLUE: Final[Color] = (55, 125, 255)
BATTERY_GREEN: Final[Color] = (106, 231, 137)
WHITE: Final[Color] = (238, 245, 251)
BLACK: Final[Color] = (0, 0, 0)

# Common semantic aliases used by rendering modules.
BACKGROUND_COLOR: Final[Color] = BACKGROUND_NAVY
WALL_COLOR: Final[Color] = WALL_DARK
FLOOR_COLOR: Final[Color] = FLOOR_DARK
TEXT_COLOR: Final[Color] = WHITE
