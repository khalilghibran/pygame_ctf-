# Development Brief for Coding Agent

Build a playable Pygame prototype using the visual references in this package.

## MVP requirements
- Top-down player movement and collision.
- One room-based laboratory level.
- Player starts without a keycard.
- Blue keycard unlocks the exit door.
- One security bot patrols between waypoints.
- Security bot has states: PATROL, CHASE, SEARCH, RETURN.
- Detection occurs only if the player is inside detection range and line-of-sight is not blocked by a wall.
- Battery meter decreases slowly over time.
- Picking up a battery restores charge.
- HUD shows battery, security state, and objective.
- Win screen appears after reaching the exit with the required keycard.

## Recommended Python modules
- main.py
- game.py
- settings.py
- player.py
- enemy.py
- level.py
- tile.py
- item.py
- door.py
- ui.py
- pathfinding.py

## Suggested classes
- Game
- Player
- SecurityBot
- TileMap
- Door
- Keycard
- BatteryPack
- Terminal
- HUD

## Enemy states
PATROL -> CHASE -> SEARCH -> RETURN -> PATROL

## MVP objective text
"Find the blue keycard and reach the exit."

## Placeholder rule
If production-ready individual sprite files are not yet available, crop approximate visuals from the reference atlas or use simple Pygame primitives while preserving filenames and APIs so artwork can be swapped later.
