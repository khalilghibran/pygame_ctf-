"""Pure grid pathfinding and line-of-sight helpers.

All coordinates are integer ``(x, y)`` tile positions.  No Pygame objects are
used, which keeps enemy navigation deterministic and straightforward to test.
"""

from __future__ import annotations

from collections.abc import Callable
from heapq import heappop, heappush
from itertools import count
from typing import TypeAlias


GridPosition: TypeAlias = tuple[int, int]
TilePredicate: TypeAlias = Callable[[GridPosition], bool]


def _validate_position(name: str, position: GridPosition) -> None:
    if (
        not isinstance(position, tuple)
        or len(position) != 2
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in position)
    ):
        raise TypeError(f"{name} must be an (x, y) tuple of integers")


def manhattan_distance(first: GridPosition, second: GridPosition) -> int:
    """Return the four-way grid distance between two positions."""

    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def neighbors4(position: GridPosition) -> tuple[GridPosition, ...]:
    """Return four adjacent cells in deterministic right/down/left/up order."""

    x, y = position
    return (x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)


def _reconstruct_path(
    came_from: dict[GridPosition, GridPosition], current: GridPosition
) -> list[GridPosition]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def astar(
    start: GridPosition,
    goal: GridPosition,
    is_walkable: TilePredicate,
) -> list[GridPosition]:
    """Find a shortest four-way path with A*.

    The returned list includes both ``start`` and ``goal``.  An empty list
    means no path exists (including when either endpoint is not walkable).
    ``is_walkable`` is responsible for bounds checks, making this function
    usable with any finite grid representation.
    """

    _validate_position("start", start)
    _validate_position("goal", goal)
    if not callable(is_walkable):
        raise TypeError("is_walkable must be callable")
    if not is_walkable(start) or not is_walkable(goal):
        return []
    if start == goal:
        return [start]

    sequence = count()
    open_heap: list[tuple[int, int, int, GridPosition]] = []
    start_h = manhattan_distance(start, goal)
    heappush(open_heap, (start_h, start_h, next(sequence), start))

    came_from: dict[GridPosition, GridPosition] = {}
    g_score: dict[GridPosition, int] = {start: 0}
    closed: set[GridPosition] = set()

    while open_heap:
        _, _, _, current = heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            return _reconstruct_path(came_from, current)
        closed.add(current)

        next_g = g_score[current] + 1
        for neighbor in neighbors4(current):
            if neighbor in closed or not is_walkable(neighbor):
                continue
            if next_g >= g_score.get(neighbor, next_g + 1):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = next_g
            heuristic = manhattan_distance(neighbor, goal)
            heappush(
                open_heap,
                (next_g + heuristic, heuristic, next(sequence), neighbor),
            )

    return []


# Descriptive alias for code that does not care which shortest-path algorithm
# provides the route.
find_path = astar


def supercover_line(
    start: GridPosition, end: GridPosition
) -> list[GridPosition]:
    """Return every grid cell touched by a center-to-center line segment.

    When a line passes exactly through a cell corner, both side-adjacent cells
    are included.  This conservative behavior prevents vision leaking through
    diagonal gaps between two walls.
    """

    _validate_position("start", start)
    _validate_position("end", end)

    x, y = start
    end_x, end_y = end
    delta_x = end_x - x
    delta_y = end_y - y
    count_x = abs(delta_x)
    count_y = abs(delta_y)
    step_x = 0 if delta_x == 0 else (1 if delta_x > 0 else -1)
    step_y = 0 if delta_y == 0 else (1 if delta_y > 0 else -1)

    cells: list[GridPosition] = [(x, y)]
    moved_x = 0
    moved_y = 0

    def append_once(position: GridPosition) -> None:
        if cells[-1] != position:
            cells.append(position)

    while moved_x < count_x or moved_y < count_y:
        decision = (1 + 2 * moved_x) * count_y - (1 + 2 * moved_y) * count_x
        if decision == 0:
            # The segment crosses a corner. Both cells touching that corner can
            # occlude sight, followed by the diagonally entered cell.
            append_once((x + step_x, y))
            append_once((x, y + step_y))
            x += step_x
            y += step_y
            moved_x += 1
            moved_y += 1
            append_once((x, y))
        elif decision < 0:
            x += step_x
            moved_x += 1
            append_once((x, y))
        else:
            y += step_y
            moved_y += 1
            append_once((x, y))

    return cells


def has_line_of_sight(
    start: GridPosition,
    end: GridPosition,
    is_transparent: TilePredicate,
    *,
    include_start: bool = False,
    include_end: bool = True,
) -> bool:
    """Return whether every tested supercover cell is transparent.

    The observer's starting cell is ignored by default; the target cell is
    checked.  Passing ``TileMap.is_walkable`` gives wall/closed-door occlusion.
    """

    if not callable(is_transparent):
        raise TypeError("is_transparent must be callable")
    cells = supercover_line(start, end)
    first = 0 if include_start else 1
    last = len(cells) if include_end else max(first, len(cells) - 1)
    return all(is_transparent(position) for position in cells[first:last])


line_of_sight = has_line_of_sight
grid_line_of_sight = has_line_of_sight

