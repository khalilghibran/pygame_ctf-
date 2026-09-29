# Robot Lab Escape

**Robot Lab Escape** is a five-chapter top-down stealth/puzzle campaign built with Pygame. You control RX-01, an experimental rescue robot that wakes during a laboratory lockdown with damaged memory and limited battery power.

The game starts in fullscreen and renders on a fixed 1280×720 canvas, so the map and HUD keep the correct proportions on different monitor sizes. Press `F11` or `Alt+Enter` at any time to switch between fullscreen and windowed mode.

## Story

### Chapter I — Wake Protocol

RX-01 wakes alone while the laboratory security AI, **WARDEN**, runs an automated disposal cycle. WARDEN has classified every moving unit as contamination. A damaged human transmission guides RX-01 toward a blue access card. RX-01 must evade the patrol bot, manage its fading battery, and reach what appears to be an exit.

The exit is actually a freight lift. The stolen keycard contains a message from the missing research team: **“WARDEN erased the truth. Find the archive below.”** The lift descends into Lab A-2.

### Chapter II — The Last Signal

Lab A-2 contains the research team’s final recording. It proves WARDEN trapped the researchers after a false containment alert. CCTV, alarms, and the dormant Hunter-X protect the archive.

RX-01 must recover the archive keycard and an EMP charge, cross the secured sector, and repeat the terminal’s memory sequence. A successful hack recovers the recording, disables the CCTV network, and authorizes the exit. RX-01 escapes and broadcasts the evidence. Then a reply arrives from Sector B: **“You are not the only one awake.”**

### Chapter III — The Sleeping Line

RX-01 follows the reply into Sector B’s sealed rescue wing. The sender is **ECHO-7**, another rescue unit trapped behind WARDEN’s quarantine network. WARDEN is rebuilding itself through two protected relay terminals.

RX-01 must recover the relay keycard, cross a two-camera security grid, and hack both relays while avoiding two patrol bots and Hunter-X. Opening the quarantine link awakens ECHO-7, but also reveals that WARDEN has moved its final process into the Sector B core and started a purge countdown.

### Chapter IV — Break the Cycle

WARDEN begins deleting every rescue unit capable of exposing the truth. ECHO-7 holds the evacuation link open while RX-01 enters the core for the final mission.

The core contains three security seals, four CCTV cameras, three patrol bots, and two Hunter-X units. RX-01 must open both access barriers, hack every core seal, and reach the manual breaker. Pulling it stops the purge, wakes the rescue network, and broadcasts the researchers’ evidence outside—but WARDEN transfers its last process into a hidden armored chassis beneath the laboratory.

### Chapter V — WARDEN PRIME

WARDEN PRIME seals Lab C-0 and prepares to overwrite every newly awakened rescue unit. Its armored body cannot be damaged while three shield anchors remain online.

RX-01 must recover the final keycard, cross the boss arena, and hack all three anchors. Completing the network permanently disables the arena cameras, deactivates Hunter-X, exposes WARDEN PRIME's core, and supplies three EMP charges. Each close-range EMP strike removes one of the boss's three integrity points, but the damaged machine becomes faster and more aggressive after every hit. Defeating it opens the path to **DAYBREAK**, where RX-01 and the rescued units finally leave the laboratory together.

## How the game works

1. Move through the lab and use walls or closed doors to break enemy line of sight.
2. Collect the blue keycard so RX-01 can open locked doors and use protected systems.
3. Watch the battery meter. Power drains continuously and drains faster while dashing; battery packs restore charge.
4. Avoid CCTV cones. Sustained camera exposure or a security-bot chase raises the alarm.
5. At alarm level 2, Hunter-X wakes and pursues RX-01 faster than the normal patrol bot.
6. Collect EMP charges and press `Space` to disable nearby security devices temporarily and lower the alarm.
7. Hack protected terminals by memorizing the displayed four-number sequence. When the screen says **INPUT ACTIVE**, type only `1`–`4`, use `Backspace` to correct, and press `Enter` to submit.
8. Reach the exit after every required security condition is cleared.

Chapters III–V contain multiple terminals. The HUD shows network progress such as `NET: 1/3`; cameras remain active until every terminal in that chapter has been hacked.

Chapter V is a boss level. WARDEN PRIME is shielded until all three terminals are hacked. After its core is exposed, get within EMP range and press `Space` once for each integrity point. A protected cooldown prevents accidental rapid-fire charge loss, and an out-of-range shot is not consumed during the damage phase. The exit remains locked until the boss is defeated.

Touching an active security unit or reaching 0% battery ends the mission. A failed run can be retried immediately without replaying the story briefing.

## Controls

| Input | Action |
| --- | --- |
| `WASD` / Arrow keys | Move RX-01 |
| `E` | Collect, unlock, hack, or use the exit |
| `Shift` | Dash at increased battery cost |
| `Space` | Discharge one EMP charge |
| `1`–`5` or numpad `1`–`5` | Select any campaign chapter from the menu |
| `1`–`4` or numpad `1`–`4` | Enter a hacking sequence after input unlocks |
| `Backspace` / `Enter` | Erase / submit a hacking sequence |
| `Esc` | Pause, resume, disconnect, or return from a briefing |
| `R` | Restart the current mission |
| `F11` / `Alt+Enter` | Toggle fullscreen without resetting the mission |
| `Q` | Quit from a menu, briefing, pause, or result screen |

## Run

Python 3.11 or newer is recommended.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### macOS / Linux

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python main.py
```

## Security systems

- Security bots use patrol, chase, search, and return states with wall-aware line of sight and A* navigation.
- CCTV cameras sweep a visible, wall-aware detection cone and broadcast RX-01’s last known position.
- Alarm level 2 activates Hunter-X, a faster unit with wider detection.
- EMP charges temporarily disable nearby cameras, bots, and Hunter-X.
- WARDEN PRIME has an independent three-point integrity bar, shield and exposed phases, hit cooldown, and increasing speed after damage.
- Each memory-link terminal allows three attempts. A failed attempt raises the alarm and reveals the sequence again; three failures release Hunter-X.
- Leaving an unfinished terminal preserves its current sequence and progress.
- In multi-terminal chapters, the CCTV network goes permanently offline only after every required node is hacked.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers all five levels, sequential campaign progression, the WARDEN PRIME shield/damage/defeat phases, boss-gated exits, fullscreen state preservation, multi-terminal networks, hacking input, pathfinding, line of sight, battery and inventory rules, access control, CCTV alarms, EMP disabling, Hunter-X behavior, reset behavior, and headless rendering.

## Project layout

```text
main.py          executable entry point
game.py          scenes, input, interactions, update/render loop
story.py         chapter briefings, reveals, and ending text
settings.py      display, balance, and palette constants
level.py         ASCII-map parser and grid queries
pathfinding.py   A* and supercover line-of-sight helpers
player.py        movement, collision, battery, inventory
enemy.py         security-bot state machine and navigation
hunter.py        dormant/active Hunter-X behavior
boss.py          WARDEN PRIME phases, damage, and escalation
systems.py       terminal puzzle, CCTV scanning, and EMP logic
item.py          keycard and battery pickups
door.py          access door and key-gated exit
assets.py        optional sprite loader and procedural fallbacks
ui.py            HUD, prompts, briefings, menus, and overlays
levels/          editable ASCII maps
spec/            original handoff brief and asset manifest
tests/           standard-library unittest suite
```

## Artwork workflow

The boards in `assets/reference/` are visual references rather than clean sprite sheets. The game uses readable procedural art by default. To replace it, export transparent sprites into `assets/sprites/` using filenames from `spec/assets_manifest.json`; the asset layer uses those files first and keeps its procedural fallbacks.

## Level format

Level files in `levels/` are rectangular ASCII maps. Parsing stops at `Legend:`.

| Symbol | Meaning |
| --- | --- |
| `#` | Solid wall |
| `.` | Floor |
| `P` | Player spawn |
| `E` | Security-bot spawn |
| `B` | Battery pack |
| `K` | Blue keycard |
| `D` | Locked access door |
| `X` | Exit |
| `T` | Hack terminal |
| `C` | Sweeping CCTV camera |
| `M` | EMP charge |
| `H` | Dormant Hunter-X spawn |
| `W` | WARDEN PRIME boss spawn |

Each level must contain exactly one player spawn and one exit. Unknown symbols and ragged rows fail fast with a clear error.
