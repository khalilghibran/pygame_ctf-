"""Security-bot state machine and navigation for Robot Lab Escape."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from enum import Enum
from typing import Any

import pygame

try:
    import settings as _settings
except ImportError:  # pragma: no cover
    _settings = None

try:
    from pathfinding import astar as _project_astar
except ImportError:  # pragma: no cover
    _project_astar = None


def _setting(names: str | Sequence[str], default: Any) -> Any:
    if isinstance(names, str):
        names = (names,)
    if _settings is not None:
        for name in names:
            if hasattr(_settings, name):
                return getattr(_settings, name)
    return default


DEFAULT_TILE_SIZE = int(_setting("TILE_SIZE", 32))
DEFAULT_PATROL_SPEED = float(
    _setting(("ENEMY_PATROL_SPEED", "BOT_PATROL_SPEED"), 80.0)
)
DEFAULT_CHASE_SPEED = float(
    _setting(("ENEMY_CHASE_SPEED", "BOT_CHASE_SPEED"), 130.0)
)
DEFAULT_DETECTION_RANGE = float(
    _setting(("ENEMY_DETECTION_RANGE", "BOT_DETECTION_RANGE"), 190.0)
)
DEFAULT_SEARCH_DURATION = float(
    _setting(
        ("ENEMY_SEARCH_DURATION", "ENEMY_SEARCH_SECONDS", "BOT_SEARCH_DURATION"),
        3.0,
    )
)
DEFAULT_REPATH_INTERVAL = float(
    _setting(("ENEMY_REPATH_INTERVAL", "ENEMY_REPATH_SECONDS"), 0.25)
)
SECURITY_RED = pygame.Color(_setting("SECURITY_RED", "#FF3B3B"))


class EnemyState(str, Enum):
    """The required security-bot states."""

    PATROL = "PATROL"
    CHASE = "CHASE"
    SEARCH = "SEARCH"
    RETURN = "RETURN"


SecurityState = EnemyState


def _position_of(value: object) -> pygame.Vector2:
    if isinstance(value, pygame.Rect):
        return pygame.Vector2(value.center)
    rect = getattr(value, "rect", None)
    if isinstance(rect, pygame.Rect):
        return pygame.Vector2(rect.center)
    position = getattr(value, "position", getattr(value, "pos", value))
    return pygame.Vector2(position)  # type: ignore[arg-type]


def _movement_rect(blocker: object) -> pygame.Rect | None:
    if hasattr(blocker, "blocks") and not bool(getattr(blocker, "blocks")):
        return None
    if hasattr(blocker, "solid") and not bool(getattr(blocker, "solid")):
        return None
    if isinstance(blocker, pygame.Rect):
        return blocker
    rect = getattr(blocker, "rect", None)
    return rect if isinstance(rect, pygame.Rect) else None


def _los_rect(blocker: object) -> pygame.Rect | None:
    if hasattr(blocker, "blocks_los") and not bool(getattr(blocker, "blocks_los")):
        return None
    return _movement_rect(blocker)


class SecurityBot(pygame.sprite.Sprite):
    """A patrol bot with PATROL -> CHASE -> SEARCH -> RETURN behavior.

    Coordinates are world-space centers.  :meth:`from_tile` is the convenient
    constructor for coordinates read from ``TileMap``.  ``update`` accepts the
    current blockers and optionally the project's ``TileMap``; when supplied,
    the bot uses the project's A* implementation for each navigation target.
    """

    PATROL = EnemyState.PATROL
    CHASE = EnemyState.CHASE
    SEARCH = EnemyState.SEARCH
    RETURN = EnemyState.RETURN

    def __init__(
        self,
        start: Sequence[float] | pygame.Vector2,
        waypoints: Iterable[Sequence[float] | pygame.Vector2] | None = None,
        *,
        tile_size: int = DEFAULT_TILE_SIZE,
        size: int | tuple[int, int] = 28,
        patrol_speed: float = DEFAULT_PATROL_SPEED,
        chase_speed: float = DEFAULT_CHASE_SPEED,
        detection_range: float = DEFAULT_DETECTION_RANGE,
        search_duration: float = DEFAULT_SEARCH_DURATION,
        repath_interval: float = DEFAULT_REPATH_INTERVAL,
        tile_map: object | None = None,
        pathfinder: Callable[..., Sequence[Sequence[int]]] | None = None,
    ) -> None:
        super().__init__()
        dimensions = (size, size) if isinstance(size, int) else size
        self.image = self._make_image((int(dimensions[0]), int(dimensions[1])))
        self.rect = self.image.get_rect(center=(round(start[0]), round(start[1])))

        self.start_position = pygame.Vector2(start)
        self.position = pygame.Vector2(start)
        self.pos = self.position
        self.tile_size = max(1, int(tile_size))
        self.patrol_speed = max(0.0, float(patrol_speed))
        self.chase_speed = max(0.0, float(chase_speed))
        self.detection_range = max(0.0, float(detection_range))
        self.search_duration = max(0.0, float(search_duration))
        self.repath_interval = max(0.01, float(repath_interval))
        self.tile_map = tile_map
        self.pathfinder = pathfinder or _project_astar

        default_route = (
            self.start_position,
            self.start_position + (6 * self.tile_size, 0),
            self.start_position + (6 * self.tile_size, 2 * self.tile_size),
            self.start_position + (0, 2 * self.tile_size),
        )
        route = list(waypoints) if waypoints is not None else default_route
        self.waypoints = [pygame.Vector2(point) for point in route] or [
            self.start_position.copy()
        ]
        if self.waypoints[0].distance_squared_to(self.start_position) > 1.0:
            self.waypoints.insert(0, self.start_position.copy())

        self.state = EnemyState.PATROL
        self.state_elapsed = 0.0
        self.search_remaining = self.search_duration
        self.patrol_index = 1 % len(self.waypoints)
        self.return_index = 0
        self.last_seen_position: pygame.Vector2 | None = None
        self.velocity = pygame.Vector2()
        self.facing = "down"
        self.disabled_remaining = 0.0

        self._path_world: list[pygame.Vector2] = []
        self._path_target_tile: tuple[int, int] | None = None
        self._repath_remaining = 0.0
        self._arrival_radius = max(2.0, self.tile_size * 0.08)

    @classmethod
    def from_tile(
        cls,
        tile: Sequence[int],
        waypoints: Iterable[Sequence[int]] | None = None,
        *,
        tile_size: int = DEFAULT_TILE_SIZE,
        **kwargs: Any,
    ) -> "SecurityBot":
        """Build a bot and optional patrol route from tile coordinates."""

        center = cls.tile_to_world(tile, tile_size)
        world_waypoints = None
        if waypoints is not None:
            world_waypoints = [cls.tile_to_world(point, tile_size) for point in waypoints]
        return cls(
            center,
            world_waypoints,
            tile_size=tile_size,
            **kwargs,
        )

    @staticmethod
    def tile_to_world(tile: Sequence[int], tile_size: int = DEFAULT_TILE_SIZE) -> pygame.Vector2:
        return pygame.Vector2(
            (int(tile[0]) + 0.5) * tile_size,
            (int(tile[1]) + 0.5) * tile_size,
        )

    def world_to_tile(self, position: Sequence[float] | pygame.Vector2) -> tuple[int, int]:
        return (int(position[0] // self.tile_size), int(position[1] // self.tile_size))

    @staticmethod
    def _make_image(size: tuple[int, int]) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        body = surface.get_rect().inflate(-4, -3)
        pygame.draw.rect(surface, (78, 88, 98), body, border_radius=7)
        pygame.draw.rect(surface, (25, 32, 39), body, width=2, border_radius=7)
        visor = pygame.Rect(0, 0, max(9, size[0] // 2), max(4, size[1] // 5))
        visor.midtop = (size[0] // 2, max(4, size[1] // 5))
        pygame.draw.rect(surface, (24, 14, 18), visor, border_radius=2)
        pygame.draw.circle(surface, SECURITY_RED, visor.center, max(2, visor.height // 3))
        return surface

    @property
    def state_name(self) -> str:
        return self.state.value

    @property
    def security_state(self) -> str:
        return self.state.value

    @property
    def last_seen(self) -> pygame.Vector2 | None:
        return self.last_seen_position

    @property
    def tile(self) -> tuple[int, int]:
        return self.world_to_tile(self.position)

    @property
    def alerted(self) -> bool:
        return self.state in (EnemyState.CHASE, EnemyState.SEARCH)

    @property
    def disabled(self) -> bool:
        return self.disabled_remaining > 0.0

    def disable(self, duration: float) -> None:
        """Temporarily halt perception, movement, and capture behavior."""

        self.disabled_remaining = max(self.disabled_remaining, max(0.0, float(duration)))
        self.velocity.update(0.0, 0.0)
        if self.state is EnemyState.CHASE:
            self.set_state(EnemyState.RETURN)

    stun = disable

    def alert_to(self, position: Sequence[float] | pygame.Vector2) -> bool:
        """Send this bot to a network-reported player position."""

        if self.disabled:
            return False
        self.last_seen_position = pygame.Vector2(position)
        self.set_state(EnemyState.CHASE)
        return True

    def set_state(self, state: EnemyState | str) -> None:
        new_state = state if isinstance(state, EnemyState) else EnemyState(state)
        if new_state is self.state:
            return
        self.state = new_state
        self.state_elapsed = 0.0
        self._path_world.clear()
        self._path_target_tile = None
        self._repath_remaining = 0.0
        if new_state is EnemyState.SEARCH:
            self.search_remaining = self.search_duration
        elif new_state is EnemyState.RETURN:
            self.return_index = self._nearest_waypoint_index()

    def sees_player(
        self,
        player: object,
        blockers: Iterable[object] = (),
        los_test: Callable[..., bool] | None = None,
    ) -> bool:
        """Return whether the player is in range with unblocked line of sight."""

        if self.disabled:
            return False
        player_position = _position_of(player)
        if self.position.distance_squared_to(player_position) > self.detection_range**2:
            return False
        if los_test is not None:
            try:
                return bool(los_test(self.position, player_position, blockers))
            except TypeError:
                return bool(los_test(self.position, player_position))

        start = (float(self.position.x), float(self.position.y))
        end = (float(player_position.x), float(player_position.y))
        for blocker in blockers:
            obstacle = _los_rect(blocker)
            if obstacle is not None and obstacle.clipline(start, end):
                return False
        return True

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
        """Advance perception, state, A* navigation, and collision by one frame."""

        seconds = max(0.0, min(float(dt), 0.1))
        if self.disabled_remaining > 0.0:
            self.disabled_remaining = max(0.0, self.disabled_remaining - seconds)
            self.velocity.update(0.0, 0.0)
            return
        blocker_list = tuple(blockers)
        navigation_map = tile_map or self.tile_map
        navigation_pathfinder = pathfinder or self.pathfinder
        self.state_elapsed += seconds
        self._repath_remaining -= seconds

        visible = self.sees_player(player, blocker_list, los_test)
        player_position = _position_of(player)
        if visible:
            self.last_seen_position = player_position.copy()
            self.set_state(EnemyState.CHASE)
        elif self.state is EnemyState.CHASE:
            self.set_state(EnemyState.SEARCH)

        target: pygame.Vector2
        speed: float
        if self.state is EnemyState.PATROL:
            target = self.waypoints[self.patrol_index]
            speed = self.patrol_speed
        elif self.state is EnemyState.CHASE:
            target = player_position if visible else (self.last_seen_position or player_position)
            speed = self.chase_speed
        elif self.state is EnemyState.SEARCH:
            target = self.last_seen_position or self.position
            speed = self.chase_speed * 0.8
            self.search_remaining = max(0.0, self.search_remaining - seconds)
            if self.search_remaining <= 0.0:
                self.set_state(EnemyState.RETURN)
                target = self.waypoints[self.return_index]
                speed = self.patrol_speed
        else:  # RETURN
            target = self.waypoints[self.return_index]
            speed = self.patrol_speed

        opened: set[tuple[int, int]] = set()
        for entry in opened_doors:
            entry_rect = getattr(entry, "rect", None)
            if isinstance(entry_rect, pygame.Rect):
                opened.add(self.world_to_tile(entry_rect.center))
            else:
                try:
                    opened.add((int(entry[0]), int(entry[1])))  # type: ignore[index]
                except (IndexError, TypeError, ValueError):
                    continue
        # Infer open door tiles when callers pass door objects with the blockers.
        for candidate in blocker_list:
            if getattr(candidate, "kind", None) == "door" and bool(
                getattr(candidate, "is_open", False)
            ):
                rect = getattr(candidate, "rect", None)
                if isinstance(rect, pygame.Rect):
                    opened.add(self.world_to_tile(rect.center))

        self._navigate(
            target,
            speed,
            seconds,
            blocker_list,
            navigation_map,
            navigation_pathfinder,
            opened,
        )

        if self.position.distance_to(target) <= self._arrival_radius:
            if self.state is EnemyState.PATROL:
                self.patrol_index = (self.patrol_index + 1) % len(self.waypoints)
                self._path_target_tile = None
            elif self.state is EnemyState.RETURN:
                self.patrol_index = (self.return_index + 1) % len(self.waypoints)
                self.set_state(EnemyState.PATROL)

    def _navigate(
        self,
        target: pygame.Vector2,
        speed: float,
        dt: float,
        blockers: Sequence[object],
        tile_map: object | None,
        pathfinder: Callable[..., Sequence[Sequence[int]]] | None,
        opened_doors: set[tuple[int, int]],
    ) -> None:
        target_tile = self.world_to_tile(target)
        needs_path = (
            target_tile != self._path_target_tile
            or not self._path_world
            or self._repath_remaining <= 0.0
        )
        if needs_path:
            self._build_path(target_tile, target, tile_map, pathfinder, opened_doors)

        while self._path_world and self.position.distance_to(self._path_world[0]) <= self._arrival_radius:
            self._path_world.pop(0)
        steering_target = self._path_world[0] if self._path_world else target
        offset = steering_target - self.position
        distance = offset.length()
        if distance <= 1e-6 or speed <= 0.0 or dt <= 0.0:
            self.velocity.update(0.0, 0.0)
            return
        direction = offset / distance
        travel = min(speed * dt, distance)
        self.velocity = direction * speed
        if abs(direction.x) > abs(direction.y):
            self.facing = "right" if direction.x > 0 else "left"
        else:
            self.facing = "down" if direction.y > 0 else "up"

        solid_rects = tuple(
            rect for blocker in blockers if (rect := _movement_rect(blocker)) is not None
        )
        collided_x = self._move_axis(direction.x * travel, 0.0, solid_rects)
        collided_y = self._move_axis(0.0, direction.y * travel, solid_rects)
        if collided_x or collided_y:
            self._repath_remaining = 0.0

    def _build_path(
        self,
        target_tile: tuple[int, int],
        target_world: pygame.Vector2,
        tile_map: object | None,
        pathfinder: Callable[..., Sequence[Sequence[int]]] | None,
        opened_doors: set[tuple[int, int]],
    ) -> None:
        self._path_target_tile = target_tile
        self._repath_remaining = self.repath_interval
        self._path_world.clear()
        if pathfinder is None or tile_map is None:
            self._path_world.append(target_world.copy())
            return

        is_walkable_method = getattr(tile_map, "is_walkable", None)
        if not callable(is_walkable_method):
            self._path_world.append(target_world.copy())
            return

        def is_walkable(tile: Sequence[int]) -> bool:
            coordinate = (int(tile[0]), int(tile[1]))
            try:
                return bool(is_walkable_method(coordinate, opened_doors=opened_doors))
            except TypeError:
                return bool(is_walkable_method(coordinate, opened_doors))

        try:
            tile_path = pathfinder(self.tile, target_tile, is_walkable)
        except TypeError:
            tile_path = pathfinder(self.tile, target_tile)
        if not tile_path:
            return
        for node in tile_path:
            point = self.tile_to_world(node, self.tile_size)
            if point.distance_to(self.position) > self._arrival_radius:
                self._path_world.append(point)
        # Preserve an exact moving target within its destination tile.
        if not self._path_world or self._path_world[-1].distance_to(target_world) > 1.0:
            self._path_world.append(target_world.copy())

    def _move_axis(
        self,
        dx: float,
        dy: float,
        blockers: Sequence[pygame.Rect],
    ) -> bool:
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

    def _nearest_waypoint_index(self) -> int:
        return min(
            range(len(self.waypoints)),
            key=lambda index: self.position.distance_squared_to(self.waypoints[index]),
        )

    def touching_player(self, player: object) -> bool:
        if self.disabled:
            return False
        player_rect = getattr(player, "rect", None)
        return isinstance(player_rect, pygame.Rect) and self.rect.colliderect(player_rect)

    has_caught = touching_player

    def reset(self, start: Sequence[float] | pygame.Vector2 | None = None) -> None:
        if start is not None:
            self.start_position.update(start)
            if self.waypoints:
                self.waypoints[0].update(start)
        self.position.update(self.start_position)
        self.rect.center = (round(self.position.x), round(self.position.y))
        self.velocity.update(0.0, 0.0)
        self.state = EnemyState.PATROL
        self.state_elapsed = 0.0
        self.search_remaining = self.search_duration
        self.patrol_index = 1 % len(self.waypoints)
        self.return_index = 0
        self.last_seen_position = None
        self.disabled_remaining = 0.0
        self._path_world.clear()
        self._path_target_tile = None
        self._repath_remaining = 0.0
        self.facing = "down"

    def draw(
        self,
        surface: pygame.Surface,
        offset: Sequence[float] | pygame.Vector2 = (0.0, 0.0),
    ) -> None:
        draw_rect = self.image.get_rect(
            center=(round(self.rect.centerx + offset[0]), round(self.rect.centery + offset[1]))
        )
        surface.blit(self.image, draw_rect)


Enemy = SecurityBot

__all__ = ["Enemy", "EnemyState", "SecurityBot", "SecurityState"]
