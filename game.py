"""Application loop and world orchestration for Robot Lab Escape."""

from __future__ import annotations

import math
import random
from enum import Enum
from pathlib import Path
from typing import Iterable

import pygame

import settings
from assets import SpriteLibrary
from boss import BossHit, WardenPrime
from door import Door, Exit
from enemy import EnemyState, SecurityBot
from hunter import HunterX
from item import BatteryPack, Keycard
from level import TileMap
from pathfinding import has_line_of_sight
from player import Player
from story import MISSION_STORIES
from systems import CCTV, EMPCharge, HackingPuzzle, HackingState, Terminal
from ui import CYAN, GREEN, NAVY, RED, STEEL, YELLOW, UI


ROOT = Path(__file__).resolve().parent
LEVEL_PATHS = (
    ROOT / "levels" / "level_01.txt",
    ROOT / "levels" / "level_02.txt",
    ROOT / "levels" / "level_03.txt",
    ROOT / "levels" / "level_04.txt",
    ROOT / "levels" / "level_05.txt",
)
LEVEL_PATH = LEVEL_PATHS[0]

if len(LEVEL_PATHS) != len(MISSION_STORIES):
    raise RuntimeError("every campaign level must have matching story data")


class Scene(str, Enum):
    MENU = "MENU"
    BRIEFING = "BRIEFING"
    PLAYING = "PLAYING"
    HACKING = "HACKING"
    PAUSED = "PAUSED"
    WON = "WON"
    CAUGHT = "CAUGHT"
    POWER_OUT = "POWER_OUT"


class Game:
    """Own the window, scene state, level entities, and gameplay loop."""

    def __init__(self, *, fullscreen: bool | None = None) -> None:
        pygame.init()
        pygame.display.set_caption(settings.GAME_TITLE)
        self.fullscreen = (
            settings.START_FULLSCREEN if fullscreen is None else bool(fullscreen)
        )
        self.screen = self._apply_display_mode()
        self.clock = pygame.time.Clock()
        self.ui = UI(settings.SCREEN_SIZE)
        self.assets = SpriteLibrary(tile_size=settings.TILE_SIZE)
        self.level_index = 0
        self.level = TileMap.from_file(LEVEL_PATHS[self.level_index])
        self._prepare_level_geometry()
        self._ambient_nodes = self._make_ambient_nodes()
        self.running = False
        self.scene = Scene.MENU
        self._animation_time = 0.0
        self.campaign_elapsed = 0.0
        self.campaign_detections = 0
        self._reset_world()
        self.scene = Scene.MENU

    def _apply_display_mode(self) -> pygame.Surface:
        """Create a scaled 1280x720 canvas in fullscreen or windowed mode."""

        # SDL's non-visual test driver can crash when its display is repeatedly
        # recreated with SCALED. It has no real monitor to make fullscreen, so
        # retain the requested state while using a logical-size test surface.
        if pygame.display.get_driver() == "dummy":
            return pygame.display.set_mode(settings.SCREEN_SIZE)

        flags = pygame.SCALED
        flags |= pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        try:
            return pygame.display.set_mode(settings.SCREEN_SIZE, flags, vsync=1)
        except pygame.error:
            # A small number of remote desktops and older SDL drivers cannot
            # create a scaled fullscreen renderer. Keep the game playable.
            self.fullscreen = False
            return pygame.display.set_mode(settings.SCREEN_SIZE, pygame.RESIZABLE)

    def _toggle_fullscreen(self) -> None:
        """Switch display mode without resetting the current mission."""

        self.fullscreen = not self.fullscreen
        self.screen = self._apply_display_mode()

    def _prepare_level_geometry(self) -> None:
        map_width = self.level.width * settings.TILE_SIZE
        map_height = self.level.height * settings.TILE_SIZE
        self.map_offset = pygame.Vector2(
            (settings.SCREEN_WIDTH - map_width) // 2,
            122,
        )
        if self.map_offset.y + map_height > settings.SCREEN_HEIGHT - 80:
            self.map_offset.y = settings.SCREEN_HEIGHT - 80 - map_height

        self.wall_rects = [
            pygame.Rect(
                x * settings.TILE_SIZE,
                y * settings.TILE_SIZE,
                settings.TILE_SIZE,
                settings.TILE_SIZE,
            )
            for x, y in self.level.walls
        ]

    def _load_level(self, index: int) -> None:
        """Load a campaign level and start a fresh run in it."""

        if not 0 <= index < len(LEVEL_PATHS):
            raise IndexError(f"level index {index} is outside the campaign")
        self.level_index = index
        self.level = TileMap.from_file(LEVEL_PATHS[index])
        self._prepare_level_geometry()
        self._reset_world()

    def _begin_mission(self, index: int) -> None:
        """Load a mission and show its authored chapter briefing."""

        self._load_level(index)
        self.scene = Scene.BRIEFING

    def _leave_briefing(self) -> None:
        """Start play after the player has read the current briefing."""

        self.scene = Scene.PLAYING
        self.ui.toast.show(MISSION_STORIES[self.level_index].start_message, CYAN, 2.8)

    def _make_ambient_nodes(self) -> tuple[tuple[int, int, int], ...]:
        generator = random.Random(101)
        return tuple(
            (
                generator.randrange(18, settings.SCREEN_WIDTH - 18),
                generator.randrange(112, settings.SCREEN_HEIGHT - 15),
                generator.choice((1, 1, 1, 2)),
            )
            for _ in range(70)
        )

    @staticmethod
    def _tile_center(tile: tuple[int, int]) -> pygame.Vector2:
        return pygame.Vector2(
            (tile[0] + 0.5) * settings.TILE_SIZE,
            (tile[1] + 0.5) * settings.TILE_SIZE,
        )

    def _patrol_route(self, spawn: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = spawn
        candidates = [spawn, (x, y + 2), (x + 5, y + 2), (x + 5, y)]
        route = [tile for tile in candidates if self.level.is_walkable(tile)]
        return route if len(route) > 1 else [spawn]

    def _reset_world(self) -> None:
        self.player = Player.from_tile(
            self.level.player_spawn,
            tile_size=settings.TILE_SIZE,
            size=settings.PLAYER_HITBOX_SIZE,
            speed=settings.PLAYER_SPEED,
            max_battery=settings.BATTERY_MAX,
            battery_drain_rate=settings.BATTERY_DRAIN_PER_SECOND,
        )
        self.keycards = [
            Keycard.from_tile(tile, tile_size=settings.TILE_SIZE, color="blue")
            for tile in self.level.keycard_positions
        ]
        self.batteries = [
            BatteryPack.from_tile(
                tile,
                tile_size=settings.TILE_SIZE,
                amount=settings.BATTERY_PICKUP_AMOUNT,
            )
            for tile in self.level.battery_positions
        ]
        self.emp_pickups = [
            EMPCharge.from_tile(tile, tile_size=settings.TILE_SIZE)
            for tile in self.level.emp_positions
        ]
        self.terminals = [
            Terminal.from_tile(tile, tile_size=settings.TILE_SIZE)
            for tile in self.level.terminal_positions
        ]
        self.cameras = [
            CCTV.from_tile(tile, tile_size=settings.TILE_SIZE, base_angle=90.0)
            for tile in self.level.camera_positions
        ]
        self.doors = [
            Door.from_tile(tile, tile_size=settings.TILE_SIZE, required_key="blue")
            for tile in self.level.door_positions
        ]
        self.exit = Exit.from_tile(
            self.level.exit_position,
            tile_size=settings.TILE_SIZE,
            required_key="blue",
        )

        self.enemies: list[SecurityBot] = []
        for spawn in self.level.enemy_spawns:
            self.enemies.append(
                SecurityBot.from_tile(
                    spawn,
                    waypoints=self._patrol_route(spawn),
                    tile_size=settings.TILE_SIZE,
                    size=settings.PLAYER_HITBOX_SIZE,
                    patrol_speed=settings.ENEMY_PATROL_SPEED,
                    chase_speed=settings.ENEMY_CHASE_SPEED,
                    detection_range=settings.ENEMY_DETECTION_RANGE,
                    search_duration=settings.ENEMY_SEARCH_SECONDS,
                    repath_interval=settings.ENEMY_REPATH_SECONDS,
                    tile_map=self.level,
                )
            )

        self.hunters: list[HunterX] = []
        for spawn in self.level.hunter_spawns:
            self.hunters.append(
                HunterX.from_tile(
                    spawn,
                    waypoints=self._patrol_route(spawn),
                    tile_size=settings.TILE_SIZE,
                    active=False,
                    patrol_speed=settings.HUNTER_PATROL_SPEED,
                    chase_speed=settings.HUNTER_CHASE_SPEED,
                    detection_range=settings.HUNTER_DETECTION_RANGE,
                    search_duration=settings.ENEMY_SEARCH_SECONDS,
                    repath_interval=settings.ENEMY_REPATH_SECONDS,
                    tile_map=self.level,
                )
            )

        self.bosses: list[WardenPrime] = []
        for spawn in self.level.boss_spawns:
            self.bosses.append(
                WardenPrime.from_tile(
                    spawn,
                    waypoints=self._patrol_route(spawn),
                    tile_size=settings.TILE_SIZE,
                    size=52,
                    patrol_speed=settings.BOSS_PATROL_SPEED,
                    chase_speed=settings.BOSS_CHASE_SPEED,
                    detection_range=settings.BOSS_DETECTION_RANGE,
                    search_duration=settings.ENEMY_SEARCH_SECONDS,
                    repath_interval=settings.ENEMY_REPATH_SECONDS,
                    tile_map=self.level,
                )
            )

        self.elapsed = 0.0
        self.security_events = 0
        self.last_enemy_states = [bot.state for bot in self.enemies]
        self.last_security_state = (
            self.enemy.state if self.enemies else EnemyState.PATROL
        )
        self.alarm_level = 0
        self.active_terminal: Terminal | None = None
        self.hacking_puzzle: HackingPuzzle | None = None
        self.hack_result_timer = 0.0
        self.dash_active = False
        self.emp_effect_remaining = 0.0
        self.emp_effect_center = self.player.position.copy()
        self.scene = Scene.PLAYING
        lab_label = MISSION_STORIES[self.level_index].lab_label
        self.ui.toast.show(
            f"{lab_label} ONLINE // LOCATE BLUE ACCESS CARD", CYAN, 2.8
        )

    @property
    def enemy(self) -> SecurityBot:
        """Return the primary security bot used by the MVP HUD."""

        return self.enemies[0]

    @property
    def blockers(self) -> tuple[object, ...]:
        return (*self.wall_rects, *self.doors, self.exit)

    @property
    def opened_door_tiles(self) -> set[tuple[int, int]]:
        return {
            tile
            for tile, door in zip(self.level.door_positions, self.doors)
            if door.is_open
        }

    @property
    def objective(self) -> str:
        story = MISSION_STORIES[self.level_index]
        if not self.player.has_keycard("blue"):
            return story.key_objective
        if self.terminals and not self.terminal_hacked:
            hacked = sum(terminal.hacked for terminal in self.terminals)
            return story.terminal_objective.format(
                hacked=hacked,
                total=len(self.terminals),
            )
        if self.bosses and not self.boss_defeated:
            boss = self.boss
            if boss is not None:
                return story.boss_objective.format(
                    health=boss.health,
                    max_health=boss.max_health,
                )
        return story.exit_objective

    @property
    def terminal_hacked(self) -> bool:
        return not self.terminals or all(terminal.hacked for terminal in self.terminals)

    @property
    def boss(self) -> WardenPrime | None:
        return self.bosses[0] if self.bosses else None

    @property
    def boss_defeated(self) -> bool:
        return not self.bosses or all(boss.defeated for boss in self.bosses)

    @property
    def exit_ready(self) -> bool:
        return self.terminal_hacked and self.boss_defeated

    @property
    def security_state_name(self) -> str:
        boss = self.boss
        if boss is not None:
            return f"PRIME:{boss.state_name}"
        active_hunters = [hunter for hunter in self.hunters if hunter.active]
        for state_name in ("CHASE", "SEARCH", "DISABLED", "RETURN", "PATROL"):
            if any(hunter.state_name == state_name for hunter in active_hunters):
                return f"X:{state_name}"
        for state in (
            EnemyState.CHASE,
            EnemyState.SEARCH,
            EnemyState.RETURN,
            EnemyState.PATROL,
        ):
            if any(bot.state is state for bot in self.enemies):
                return state.value
        return "CLEAR"

    def run(self, *, max_frames: int | None = None) -> None:
        """Run until quit; ``max_frames`` supports deterministic smoke tests."""

        self.running = True
        frames = 0
        while self.running and (max_frames is None or frames < max_frames):
            dt = min(self.clock.tick(settings.FPS) / 1000.0, 0.05)
            self._animation_time += dt
            self._handle_events()
            if self.scene is Scene.PLAYING:
                self._update(dt)
            elif self.scene is Scene.HACKING:
                self._update_hacking(dt)
            self.ui.toast.update(dt)
            self._draw()
            pygame.display.flip()
            frames += 1
        if max_frames is None:
            pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type != pygame.KEYDOWN:
                continue

            alt_enter = event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and bool(
                getattr(event, "mod", 0) & pygame.KMOD_ALT
            )
            if event.key == pygame.K_F11 or alt_enter:
                self._toggle_fullscreen()
                continue

            if self.scene is Scene.HACKING:
                self._handle_hacking_key(event)
                continue

            if event.key == pygame.K_q and self.scene is not Scene.PLAYING:
                self.running = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.scene is Scene.MENU:
                    self._begin_mission(0)
                elif self.scene is Scene.BRIEFING:
                    self._leave_briefing()
                elif self.scene in (Scene.WON, Scene.CAUGHT, Scene.POWER_OUT):
                    if self.scene is Scene.WON and self.level_index + 1 < len(LEVEL_PATHS):
                        self._begin_mission(self.level_index + 1)
                    else:
                        self._reset_world()
            elif event.key in (pygame.K_1, pygame.K_KP1) and self.scene is Scene.MENU:
                self._begin_mission(0)
            elif event.key in (pygame.K_2, pygame.K_KP2) and self.scene is Scene.MENU:
                self._begin_mission(1)
            elif event.key in (pygame.K_3, pygame.K_KP3) and self.scene is Scene.MENU:
                self._begin_mission(2)
            elif event.key in (pygame.K_4, pygame.K_KP4) and self.scene is Scene.MENU:
                self._begin_mission(3)
            elif event.key in (pygame.K_5, pygame.K_KP5) and self.scene is Scene.MENU:
                self._begin_mission(4)
            elif event.key == pygame.K_SPACE and self.scene is Scene.BRIEFING:
                self._leave_briefing()
            elif event.key == pygame.K_r and self.scene is not Scene.MENU:
                self._reset_world()
            elif event.key == pygame.K_ESCAPE:
                if self.scene is Scene.PLAYING:
                    self.scene = Scene.PAUSED
                elif self.scene is Scene.PAUSED:
                    self.scene = Scene.PLAYING
                elif self.scene is Scene.BRIEFING:
                    self.scene = Scene.MENU
                elif self.scene is Scene.MENU:
                    self.running = False
            elif event.key == pygame.K_e and self.scene is Scene.PLAYING:
                self._interact()
            elif event.key == pygame.K_SPACE and self.scene is Scene.PLAYING:
                self._activate_emp()

    def _handle_hacking_key(self, event: pygame.event.Event) -> None:
        puzzle = self.hacking_puzzle
        if puzzle is None:
            self.scene = Scene.PLAYING
            return
        if event.key == pygame.K_ESCAPE:
            self.scene = Scene.PLAYING
            self.active_terminal = None
            self.hacking_puzzle = None
            self.ui.toast.show("TERMINAL LINK CLOSED", STEEL, 1.2)
            return
        if event.key == pygame.K_BACKSPACE:
            puzzle.backspace()
            return
        symbol_keys = {
            pygame.K_1: "1",
            pygame.K_2: "2",
            pygame.K_3: "3",
            pygame.K_4: "4",
            pygame.K_KP1: "1",
            pygame.K_KP2: "2",
            pygame.K_KP3: "3",
            pygame.K_KP4: "4",
        }
        symbol = symbol_keys.get(event.key)
        if symbol is None:
            typed = getattr(event, "unicode", "")
            symbol = typed if typed in "1234" and len(typed) == 1 else None
        if symbol is not None:
            puzzle.enter_symbol(symbol)
            return
        if event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return

        attempts_before = puzzle.attempts_remaining
        result = puzzle.submit()
        if result is True:
            if self.active_terminal is not None:
                self.active_terminal.mark_hacked()
            self.scene = Scene.PLAYING
            hacked = sum(terminal.hacked for terminal in self.terminals)
            total = len(self.terminals)
            if self.terminal_hacked:
                for camera in self.cameras:
                    camera.disable_permanently()
                for hunter in self.hunters:
                    hunter.deactivate()
                for boss in self.bosses:
                    if not boss.defeated:
                        boss.alert_to(self.player.position)
                        self.player.add_emp_charge(boss.max_health)
                self.alarm_level = 0
                message = MISSION_STORIES[self.level_index].network_clear_message
            else:
                self.alarm_level = max(0, self.alarm_level - 1)
                message = f"NETWORK NODE {hacked}/{total} OFFLINE // CONTINUE"
            self.ui.toast.show(message, GREEN, 2.5)
            self.active_terminal = None
            self.hacking_puzzle = None
        elif puzzle.attempts_remaining < attempts_before:
            self._raise_alarm(1, self.player.position, "HACK TRACE")
            if puzzle.failed:
                self.scene = Scene.PLAYING
                self.ui.toast.show("HACK FAILED // HUNTER-X RELEASED", RED, 2.5)
                self.active_terminal = None
                self.hacking_puzzle = None

    def _update_hacking(self, dt: float) -> None:
        if self.hacking_puzzle is None:
            self.scene = Scene.PLAYING
            return
        self.hacking_puzzle.update(dt)

    def _movement_input(self) -> pygame.Vector2:
        keys = pygame.key.get_pressed()
        return pygame.Vector2(
            float(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - float(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            float(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - float(keys[pygame.K_w] or keys[pygame.K_UP]),
        )

    def _line_of_sight(
        self,
        start: pygame.Vector2,
        end: pygame.Vector2,
        _blockers: Iterable[object] = (),
    ) -> bool:
        start_tile = (int(start.x // settings.TILE_SIZE), int(start.y // settings.TILE_SIZE))
        end_tile = (int(end.x // settings.TILE_SIZE), int(end.y // settings.TILE_SIZE))
        opened = self.opened_door_tiles
        return has_line_of_sight(
            start_tile,
            end_tile,
            lambda tile: self.level.is_walkable(tile, opened),
        )

    def _update(self, dt: float) -> None:
        self.elapsed += dt
        self.campaign_elapsed += dt
        self.emp_effect_remaining = max(0.0, self.emp_effect_remaining - dt)

        movement = self._movement_input()
        keys = pygame.key.get_pressed()
        self.dash_active = bool(
            movement.length_squared()
            and (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            and self.player.battery > 1.0
        )
        self.player.speed = settings.PLAYER_SPEED * (
            settings.DASH_SPEED_MULTIPLIER if self.dash_active else 1.0
        )
        self.player.update(dt, movement, self.blockers)
        self.player.speed = settings.PLAYER_SPEED
        drain_rate = settings.BATTERY_DRAIN_PER_SECOND
        if self.dash_active:
            drain_rate += settings.DASH_BATTERY_DRAIN_PER_SECOND
        if self.player.drain_battery(dt, drain_rate):
            self.scene = Scene.POWER_OUT
            return

        for camera in self.cameras:
            if camera.update(dt, self.player.position, self._line_of_sight):
                self.security_events += 1
                self.campaign_detections += 1
                self._raise_alarm(1, self.player.position, "CCTV LOCK")

        opened = self.opened_door_tiles
        previous_enemy_states = tuple(self.last_enemy_states)
        for bot in self.enemies:
            bot.update(
                dt,
                self.player,
                self.blockers,
                tile_map=self.level,
                opened_doors=opened,
                los_test=self._line_of_sight,
            )
            if bot.touching_player(self.player):
                self.scene = Scene.CAUGHT
                return

        for hunter in self.hunters:
            hunter.update(
                dt,
                self.player,
                self.blockers,
                tile_map=self.level,
                opened_doors=opened,
                los_test=self._line_of_sight,
            )
            if hunter.touching_player(self.player):
                self.scene = Scene.CAUGHT
                return

        for boss in self.bosses:
            boss.update(
                dt,
                self.player,
                self.blockers,
                tile_map=self.level,
                opened_doors=opened,
                los_test=self._line_of_sight,
            )
            if boss.touching_player(self.player):
                self.scene = Scene.CAUGHT
                return

        current_enemy_states = tuple(bot.state for bot in self.enemies)
        chase_started = any(
            state is EnemyState.CHASE
            and (index >= len(previous_enemy_states) or previous_enemy_states[index] is not EnemyState.CHASE)
            for index, state in enumerate(current_enemy_states)
        )
        chase_ended = (
            any(state is EnemyState.CHASE for state in previous_enemy_states)
            and not any(state is EnemyState.CHASE for state in current_enemy_states)
        )
        if chase_started:
            self.security_events += 1
            self.campaign_detections += 1
            self._raise_alarm(1, self.player.position, "SECURITY BREACH")
        elif chase_ended:
            self.ui.toast.show("SECURITY SWEEP ENDED", GREEN, 1.5)
        self.last_enemy_states = [bot.state for bot in self.enemies]
        if self.enemies:
            self.last_security_state = self.enemy.state

    def _raise_alarm(
        self,
        amount: int,
        last_seen: pygame.Vector2 | tuple[float, float],
        source: str,
    ) -> None:
        previous = self.alarm_level
        self.alarm_level = min(
            settings.ALARM_MAX_LEVEL, self.alarm_level + max(0, int(amount))
        )
        for bot in self.enemies:
            bot.alert_to(last_seen)
        for boss in self.bosses:
            boss.alert_to(last_seen)
        if self.alarm_level >= settings.ALARM_HUNTER_LEVEL:
            for hunter in self.hunters:
                hunter.activate(last_seen)
        if self.alarm_level > previous:
            self.ui.toast.show(
                f"{source} // ALARM LEVEL {self.alarm_level}", RED, 2.0
            )

    def _activate_emp(self) -> bool:
        nearby_boss = next(
            (
                boss
                for boss in self.bosses
                if not boss.defeated
                and boss.position.distance_to(self.player.position)
                <= settings.EMP_RADIUS
            ),
            None,
        )
        if (
            self.bosses
            and self.terminal_hacked
            and not self.boss_defeated
            and nearby_boss is None
        ):
            self.ui.toast.show(
                "WARDEN PRIME OUT OF EMP RANGE // MOVE CLOSER",
                YELLOW,
                1.4,
            )
            return False
        if (
            nearby_boss is not None
            and self.terminal_hacked
            and not nearby_boss.ready_for_emp
        ):
            self.ui.toast.show(
                f"EMP COUPLING RECHARGING // {nearby_boss.damage_cooldown_remaining:.1f}s",
                YELLOW,
                1.2,
            )
            return False
        if not self.player.use_emp_charge():
            self.ui.toast.show("NO EMP CHARGE AVAILABLE", STEEL, 1.3)
            return False
        self.emp_effect_center = self.player.position.copy()
        self.emp_effect_remaining = settings.EMP_EFFECT_SECONDS
        affected = 0
        for device in (*self.cameras, *self.enemies, *self.hunters):
            position = pygame.Vector2(getattr(device, "position", device.rect.center))
            if position.distance_to(self.player.position) <= settings.EMP_RADIUS:
                device.disable(settings.EMP_DISABLE_SECONDS)
                affected += 1

        boss_hit: BossHit | None = None
        if nearby_boss is not None:
            boss_hit = nearby_boss.receive_emp(shield_down=self.terminal_hacked)
            if boss_hit is BossHit.COOLDOWN:
                self.player.add_emp_charge()
                self.ui.toast.show("EMP COUPLING RECHARGING", YELLOW, 1.1)
                return False
            affected += 1

        self.alarm_level = max(0, self.alarm_level - 1)
        if boss_hit is BossHit.SHIELDED:
            self.ui.toast.show(
                "WARDEN SHIELD ABSORBED EMP // HACK ALL ANCHORS",
                YELLOW,
                2.2,
            )
        elif boss_hit is BossHit.DAMAGED:
            self.ui.toast.show(
                f"DIRECT HIT // WARDEN INTEGRITY {nearby_boss.health}/{nearby_boss.max_health}",
                RED,
                2.0,
            )
        elif boss_hit is BossHit.DEFEATED:
            self.ui.toast.show(
                "WARDEN PRIME DEFEATED // SURFACE EXIT OPEN",
                GREEN,
                2.8,
            )
        else:
            self.ui.toast.show(
                f"EMP DISCHARGED // {affected} SECURITY DEVICE(S) DISABLED",
                CYAN,
                2.0,
            )
        return True

    def _interaction_target(self) -> object | None:
        interaction_rect = self.player.interaction_rect(20)
        candidates: list[object] = []
        candidates.extend(item for item in self.keycards if item.active)
        candidates.extend(item for item in self.batteries if item.active)
        candidates.extend(item for item in self.emp_pickups if item.active)
        candidates.extend(self.terminals)
        candidates.extend(door for door in self.doors if not door.is_open)
        candidates.append(self.exit)
        nearby = [
            candidate
            for candidate in candidates
            if interaction_rect.colliderect(getattr(candidate, "rect"))
        ]
        if not nearby:
            return None
        return min(
            nearby,
            key=lambda candidate: pygame.Vector2(candidate.rect.center).distance_squared_to(
                self.player.position
            ),
        )

    def _prompt_for(self, target: object | None) -> str:
        if isinstance(target, Keycard):
            return "[E]  COLLECT BLUE KEYCARD"
        if isinstance(target, BatteryPack):
            return "[E]  RESTORE BATTERY"
        if isinstance(target, EMPCharge):
            return "[E]  COLLECT EMP CHARGE"
        if isinstance(target, Terminal):
            if target.hacked:
                return "[E]  TERMINAL NODE OFFLINE"
            if not self.player.has_keycard():
                return "[E]  TERMINAL REQUIRES BLUE KEYCARD"
            return "[E]  HACK SECURITY TERMINAL"
        if isinstance(target, Exit):
            if not self.player.has_keycard():
                return "[E]  EXIT REQUIRES BLUE KEYCARD"
            if not self.terminal_hacked:
                return "[E]  EXIT LOCKDOWN — HACK TERMINAL"
            if not self.boss_defeated:
                return "[E]  EXIT LOCKDOWN — DEFEAT WARDEN PRIME"
            return "[E]  OPEN EXIT"
        if isinstance(target, Door):
            return "[E]  OPEN ACCESS DOOR" if self.player.has_keycard() else "[E]  BLUE ACCESS REQUIRED"
        return ""

    def _interact(self) -> None:
        target = self._interaction_target()
        if target is None:
            self.ui.toast.show("NO INTERACTIVE DEVICE IN RANGE", STEEL, 1.1)
            return

        if isinstance(target, Keycard):
            if target.interact(self.player):
                self.ui.toast.show("BLUE KEYCARD ACQUIRED // ACCESS UPDATED", CYAN, 2.4)
            return
        if isinstance(target, BatteryPack):
            before = self.player.battery
            if target.interact(self.player):
                restored = self.player.battery - before
                self.ui.toast.show(f"POWER RESTORED +{restored:.0f}%", GREEN, 1.8)
            else:
                self.ui.toast.show("BATTERY ALREADY AT FULL CHARGE", YELLOW, 1.5)
            return
        if isinstance(target, EMPCharge):
            if target.interact(self.player):
                self.ui.toast.show("EMP CHARGE ACQUIRED // SPACE TO DISCHARGE", CYAN, 2.1)
            else:
                self.ui.toast.show("EMP STORAGE FULL", YELLOW, 1.4)
            return
        if isinstance(target, Terminal):
            if target.hacked:
                self.ui.toast.show("TERMINAL NODE ALREADY OFFLINE", GREEN, 1.4)
                return
            puzzle = target.begin_hack(
                self.player,
                rng=random.Random(self.level_index * 10_000 + int(self.elapsed * 1000)),
            )
            if puzzle is None:
                self.ui.toast.show("TERMINAL ACCESS REQUIRES BLUE KEYCARD", RED, 1.8)
                return
            self.active_terminal = target
            self.hacking_puzzle = puzzle
            self.scene = Scene.HACKING
            return
        if isinstance(target, Exit):
            if not self.terminal_hacked:
                self.ui.toast.show("EXIT LOCKDOWN // HACK SECURITY TERMINAL", RED, 1.9)
                return
            if not self.boss_defeated:
                self.ui.toast.show(
                    "EXIT LOCKDOWN // DEFEAT WARDEN PRIME WITH EMP",
                    RED,
                    2.0,
                )
                return
            if target.interact(self.player):
                self.scene = Scene.WON
            else:
                self.ui.toast.show("EXIT LOCKED // BLUE KEYCARD REQUIRED", RED, 1.8)
            return
        if isinstance(target, Door):
            if target.interact(self.player):
                self.ui.toast.show("ACCESS GRANTED // DOOR UNLOCKED", GREEN, 1.8)
            else:
                self.ui.toast.show("ACCESS DENIED // BLUE KEYCARD REQUIRED", RED, 1.8)

    def _screen_rect(self, world_rect: pygame.Rect) -> pygame.Rect:
        return world_rect.move(round(self.map_offset.x), round(self.map_offset.y))

    def _draw_background(self) -> None:
        self.screen.fill(NAVY)
        for x in range(0, settings.SCREEN_WIDTH, 64):
            pygame.draw.line(self.screen, (13, 30, 46), (x, 0), (x, settings.SCREEN_HEIGHT))
        for y in range(0, settings.SCREEN_HEIGHT, 64):
            pygame.draw.line(self.screen, (13, 30, 46), (0, y), (settings.SCREEN_WIDTH, y))
        pulse = 0.45 + 0.35 * math.sin(self._animation_time * 1.4)
        for x, y, radius in self._ambient_nodes:
            pygame.draw.circle(self.screen, (16, int(48 + 18 * pulse), 70), (x, y), radius)

    def _draw_floor(self, tile: tuple[int, int]) -> None:
        x, y = tile
        position = (
            round(self.map_offset.x + x * settings.TILE_SIZE),
            round(self.map_offset.y + y * settings.TILE_SIZE),
        )
        variants = ("floor_clean.png", "floor_dark.png", "floor_panel.png")
        tile_image = self.assets.get(
            variants[(x * 7 + y * 11) % len(variants)], settings.TILE_SIZE
        )
        if tile_image is not None:
            self.screen.blit(tile_image, position)

    def _draw_wall(self, tile: tuple[int, int]) -> None:
        x, y = tile
        position = (
            round(self.map_offset.x + x * settings.TILE_SIZE),
            round(self.map_offset.y + y * settings.TILE_SIZE),
        )
        variants = ("wall_top.png", "wall_side.png", "wall_corner.png")
        tile_image = self.assets.get(
            variants[(x * 5 + y * 3) % len(variants)], settings.TILE_SIZE
        )
        if tile_image is not None:
            self.screen.blit(tile_image, position)

    def _blit_world_center(
        self,
        image: pygame.Surface | None,
        center: tuple[int, int] | pygame.Vector2,
    ) -> None:
        if image is None:
            return
        screen_center = (
            round(center[0] + self.map_offset.x),
            round(center[1] + self.map_offset.y),
        )
        self.screen.blit(image, image.get_rect(center=screen_center))

    def _draw_security_field(self, bot: SecurityBot) -> None:
        if getattr(bot, "dormant", False) or getattr(bot, "defeated", False):
            return
        center = (
            round(bot.position.x + self.map_offset.x),
            round(bot.position.y + self.map_offset.y),
        )
        radius = round(bot.detection_range)
        diameter = radius * 2 + 6
        layer = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        local_center = (diameter // 2, diameter // 2)
        disabled = bool(getattr(bot, "disabled", False))
        color = CYAN if disabled else RED if bot.state is EnemyState.CHASE else (182, 62, 68)
        alpha = 10 if disabled else 22 if bot.state is EnemyState.PATROL else 38
        pygame.draw.circle(layer, (*color, alpha), local_center, radius)
        pygame.draw.circle(layer, (*color, 90), local_center, radius, 2)
        self.screen.blit(layer, (center[0] - diameter // 2, center[1] - diameter // 2))
        if bot.sees_player(self.player, self.blockers, self._line_of_sight):
            pygame.draw.line(
                self.screen,
                RED,
                center,
                (
                    round(self.player.position.x + self.map_offset.x),
                    round(self.player.position.y + self.map_offset.y),
                ),
                2,
            )

    def _draw_camera_cone(self, camera: CCTV) -> None:
        if camera.disabled:
            return
        center = pygame.Vector2(camera.position) + self.map_offset
        half = camera.fov_degrees / 2.0
        points = [center]
        opened = self.opened_door_tiles
        for step in range(25):
            angle = camera.angle - half + camera.fov_degrees * step / 24
            direction = pygame.Vector2(1, 0).rotate(angle)
            endpoint = pygame.Vector2(camera.position)
            for distance in range(6, round(camera.range) + 1, 6):
                candidate = pygame.Vector2(camera.position) + direction * distance
                tile = (
                    int(candidate.x // settings.TILE_SIZE),
                    int(candidate.y // settings.TILE_SIZE),
                )
                if not self.level.is_walkable(tile, opened):
                    break
                endpoint = candidate
            points.append(endpoint + self.map_offset)
        layer = pygame.Surface(settings.SCREEN_SIZE, pygame.SRCALPHA)
        alpha = 58 if camera.detection_ratio >= 1.0 else 28
        pygame.draw.polygon(layer, (*RED, alpha), points)
        pygame.draw.lines(layer, (*RED, 85), False, points[1:], 1)
        self.screen.blit(layer, (0, 0))

    def _draw_world(self) -> None:
        map_rect = pygame.Rect(
            round(self.map_offset.x),
            round(self.map_offset.y),
            self.level.width * settings.TILE_SIZE,
            self.level.height * settings.TILE_SIZE,
        )
        glow_rect = map_rect.inflate(12, 12)
        pygame.draw.rect(self.screen, (5, 13, 22), glow_rect, border_radius=5)
        pygame.draw.rect(self.screen, CYAN, glow_rect, 1, border_radius=5)

        for tile, symbol in self.level.iter_tiles():
            if symbol == "#":
                self._draw_wall(tile)
            else:
                self._draw_floor(tile)

        # Industrial hazard marking around the locked access tile.
        for tile in self.level.door_positions:
            rect = self._screen_rect(
                pygame.Rect(tile[0] * settings.TILE_SIZE, tile[1] * settings.TILE_SIZE, settings.TILE_SIZE, settings.TILE_SIZE)
            )
            for x in range(rect.left - 8, rect.right + 8, 12):
                pygame.draw.line(self.screen, YELLOW, (x, rect.bottom + 4), (x + 7, rect.bottom + 4), 3)

        for camera in self.cameras:
            self._draw_camera_cone(camera)
        for bot in (*self.enemies, *self.hunters, *self.bosses):
            self._draw_security_field(bot)
        for door in self.doors:
            name = "door_open.png" if door.is_open else "door_locked.png"
            self._blit_world_center(self.assets.get(name, settings.TILE_SIZE), door.rect.center)
        self._blit_world_center(
            self.assets.get("exit_door.png", settings.TILE_SIZE), self.exit.rect.center
        )
        for battery in self.batteries:
            if battery.active:
                self._blit_world_center(
                    self.assets.get("battery_pack.png", (30, 38)), battery.rect.center
                )
        for keycard in self.keycards:
            if keycard.active:
                self._blit_world_center(
                    self.assets.get("keycard_blue.png", (34, 22)), keycard.rect.center
                )
        for charge in self.emp_pickups:
            if charge.active:
                self._blit_world_center(
                    self.assets.get("emp_charge.png", (34, 34)), charge.rect.center
                )
        for terminal in self.terminals:
            terminal_image = (
                self.assets.get("terminal.png", (44, 44))
                if self.assets.has("terminal.png")
                else self.assets.terminal(terminal.hacked, (44, 44))
            )
            self._blit_world_center(
                terminal_image, terminal.rect.center
            )
        for camera in self.cameras:
            camera_name = f"cctv_{camera.direction}.png"
            camera_image = (
                self.assets.get(camera_name, (38, 38))
                if self.assets.has(camera_name) and not camera.disabled
                else self.assets.cctv(camera.direction, camera.disabled, (38, 38))
            )
            self._blit_world_center(
                camera_image,
                camera.rect.center,
            )

        frame = int(self._animation_time * 5) % 2
        for bot in self.enemies:
            action = "walk" if bot.velocity.length_squared() else "idle"
            name = f"security_{action}_{bot.facing}"
            if action == "walk":
                name += f"_{frame}"
            self._blit_world_center(self.assets.get(name + ".png", (44, 44)), bot.rect.center)
        for hunter in self.hunters:
            hunter_name = (
                "hunter_attack.png"
                if hunter.alerted
                else "hunter_walk_0.png"
                if hunter.velocity.length_squared()
                else "hunter_idle.png"
            )
            self._blit_world_center(
                self.assets.get(hunter_name, (58, 48)), hunter.rect.center
            )
        for boss in self.bosses:
            self._blit_world_center(
                self.assets.warden_prime(
                    shielded=not self.terminal_hacked,
                    damaged=0 < boss.health < boss.max_health,
                    defeated=boss.defeated,
                    size=(78, 68),
                ),
                boss.rect.center,
            )

        action = "walk" if self.player.is_moving else "idle"
        player_name = f"player_{action}_{self.player.facing}"
        if action == "walk":
            player_name += f"_{frame}"
        self._blit_world_center(
            self.assets.get(player_name + ".png", (44, 44)), self.player.rect.center
        )

        if self.emp_effect_remaining > 0.0:
            progress = 1.0 - self.emp_effect_remaining / settings.EMP_EFFECT_SECONDS
            radius = max(8, round(settings.EMP_RADIUS * progress))
            alpha = round(210 * (1.0 - progress))
            wave = self.assets.emp_wave(radius, alpha)
            self._blit_world_center(wave, self.emp_effect_center)

        pygame.draw.rect(self.screen, (111, 139, 158), map_rect, 2)

    def _draw(self) -> None:
        self._draw_background()
        self._draw_world()
        state = self.security_state_name
        prompt = self._prompt_for(self._interaction_target()) if self.scene is Scene.PLAYING else ""
        self.ui.draw_hud(
            self.screen,
            battery=self.player.battery,
            max_battery=self.player.max_battery,
            has_keycard=self.player.has_keycard(),
            security_state=state,
            objective=self.objective,
            elapsed=self.elapsed,
            prompt=prompt,
            emp_charges=self.player.emp_charges,
            alarm_level=self.alarm_level,
            level_label=MISSION_STORIES[self.level_index].lab_label,
            terminal_hacked=self.terminal_hacked if self.terminals else None,
            terminal_progress=(
                sum(terminal.hacked for terminal in self.terminals),
                len(self.terminals),
            )
            if self.terminals
            else None,
            boss_name="WARDEN PRIME" if self.boss is not None else None,
            boss_health=self.boss.health if self.boss is not None else 0,
            boss_max_health=self.boss.max_health if self.boss is not None else 0,
            boss_shielded=bool(self.boss is not None and not self.terminal_hacked),
            boss_defeated=bool(self.boss is not None and self.boss.defeated),
            dash_active=self.dash_active,
        )

        pulse = (math.sin(self._animation_time * 3.0) + 1.0) * 0.5
        if self.scene is Scene.MENU:
            self.ui.draw_title(self.screen, pulse)
        elif self.scene is Scene.BRIEFING:
            self.ui.draw_briefing(
                self.screen,
                MISSION_STORIES[self.level_index],
            )
        elif self.scene is Scene.HACKING and self.hacking_puzzle is not None:
            self.ui.draw_hacking(self.screen, self.hacking_puzzle)
        elif self.scene is Scene.PAUSED:
            self.ui.draw_overlay(
                self.screen,
                "MISSION PAUSED",
                "RX-01 is holding position.",
                ("ESC  Resume", "R  Restart mission", "Q  Quit to desktop"),
                color=CYAN,
            )
        elif self.scene is Scene.WON:
            minutes, seconds = divmod(int(self.elapsed), 60)
            has_next = self.level_index + 1 < len(LEVEL_PATHS)
            story = MISSION_STORIES[self.level_index]
            action = (
                f"ENTER  Continue to {MISSION_STORIES[self.level_index + 1].chapter}     R  Retry"
                if has_next
                else "ENTER / R  Run again     Q  Quit"
            )
            self.ui.draw_overlay(
                self.screen,
                story.clear_title,
                story.clear_subtitle,
                (
                    *story.clear_lines,
                    f"TIME  {minutes:02d}:{seconds:02d}",
                    f"DETECTIONS  {self.security_events}",
                    f"BATTERY  {self.player.battery:.0f}%",
                    action,
                ),
                color=GREEN,
            )
        elif self.scene is Scene.CAUGHT:
            self.ui.draw_overlay(
                self.screen,
                "UNIT CAPTURED",
                "The security bot intercepted RX-01.",
                ("Break line of sight and use walls as cover.", "ENTER / R  Retry mission     Q  Quit"),
                color=RED,
            )
        elif self.scene is Scene.POWER_OUT:
            self.ui.draw_overlay(
                self.screen,
                "POWER DEPLETED",
                "RX-01 can no longer continue.",
                ("Find the battery pack before charge reaches zero.", "ENTER / R  Retry mission     Q  Quit"),
                color=YELLOW,
            )


__all__ = ["Game", "Scene"]
