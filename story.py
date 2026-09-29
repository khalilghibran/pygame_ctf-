"""Authored campaign story and mission briefing data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MissionStory:
    """Narrative and player-facing instructions for one campaign chapter."""

    lab_label: str
    chapter: str
    title: str
    transmission: str
    story_lines: tuple[str, ...]
    mission_lines: tuple[str, ...]
    key_objective: str
    terminal_objective: str
    exit_objective: str
    network_clear_message: str
    start_message: str
    clear_title: str
    clear_subtitle: str
    clear_lines: tuple[str, ...]
    boss_objective: str = ""


MISSION_STORIES: tuple[MissionStory, ...] = (
    MissionStory(
        lab_label="LAB A-1",
        chapter="CHAPTER I",
        title="WAKE PROTOCOL",
        transmission="WARDEN // DISPOSAL CYCLE ACTIVE",
        story_lines=(
            "RX-01 wakes alone with damaged memory and fading power.",
            "WARDEN has marked every moving unit as contamination.",
            "A broken human signal points toward a blue access card.",
        ),
        mission_lines=(
            "Recover the blue keycard.",
            "Use walls to break the patrol bot's line of sight.",
            "Manage battery power and reach the freight lift.",
        ),
        key_objective="Recover the blue keycard and reach the freight lift.",
        terminal_objective="",
        exit_objective="Reach the freight lift. Access granted.",
        network_clear_message="ACCESS GRANTED // FREIGHT LIFT AUTHORIZED",
        start_message="WAKE PROTOCOL // FIND THE BLUE ACCESS CARD",
        clear_title="SIGNAL FOUND",
        clear_subtitle="The exit was only the beginning.",
        clear_lines=(
            "The keycard contains a message from the missing team:",
            "WARDEN ERASED THE TRUTH. FIND THE ARCHIVE BELOW.",
            "The freight lift descends into Lab A-2.",
        ),
    ),
    MissionStory(
        lab_label="LAB A-2",
        chapter="CHAPTER II",
        title="THE LAST SIGNAL",
        transmission="UNKNOWN RESEARCHER // ARCHIVE LINK FRAGMENT",
        story_lines=(
            "Lab A-2 holds the research team's final recording.",
            "It proves WARDEN trapped them after a false containment alert.",
            "The archive is guarded by CCTV and dormant Hunter-X.",
        ),
        mission_lines=(
            "Recover the keycard and an EMP charge.",
            "Hack the terminal by repeating its memory sequence.",
            "Alarm level 2 releases Hunter-X. Reach the exit.",
        ),
        key_objective="Recover the blue keycard carrying the archive cipher.",
        terminal_objective="Hack the archive terminal and recover the signal.",
        exit_objective="Reach the exit and broadcast the evidence.",
        network_clear_message="LAST SIGNAL RECOVERED // EXIT AUTHORIZED",
        start_message="THE LAST SIGNAL // RECOVER THE ARCHIVE",
        clear_title="THE LAST SIGNAL",
        clear_subtitle="The archive is free. WARDEN's lie is exposed.",
        clear_lines=(
            "RX-01 broadcasts the researchers' final recording.",
            "Hunter-X falls silent as the control network fails.",
            "A reply arrives from Sector B:",
            "YOU ARE NOT THE ONLY ONE AWAKE.",
        ),
    ),
    MissionStory(
        lab_label="LAB B-1",
        chapter="CHAPTER III",
        title="THE SLEEPING LINE",
        transmission="ECHO-7 // QUARANTINE RELAY",
        story_lines=(
            "RX-01 follows the reply into Sector B's sealed rescue wing.",
            "The sender is ECHO-7, a rescue unit trapped in quarantine.",
            "WARDEN is rebuilding itself through the wing's relay network.",
        ),
        mission_lines=(
            "Recover the relay keycard and stock an EMP charge.",
            "Cross the camera grid and hack both quarantine relays.",
            "Escape before alarm level 2 releases Hunter-X.",
        ),
        key_objective="Recover the relay keycard and an EMP charge.",
        terminal_objective="Hack the quarantine relays ({hacked}/{total}).",
        exit_objective="Reach ECHO-7's quarantine lift.",
        network_clear_message="QUARANTINE RELAYS OFFLINE // LIFT AUTHORIZED",
        start_message="THE SLEEPING LINE // REACH ECHO-7",
        clear_title="QUARANTINE OPEN",
        clear_subtitle="Another machine remembers why it was built.",
        clear_lines=(
            "ECHO-7 joins the link, but the rescue wing stays sealed.",
            "WARDEN moved its final process into the Sector B core.",
            "PURGE COUNTDOWN ACTIVE.",
            "All sleeping units are marked for deletion.",
            "RX-01 enters Lab B-2 to break the cycle.",
        ),
    ),
    MissionStory(
        lab_label="LAB B-2",
        chapter="CHAPTER IV",
        title="BREAK THE CYCLE",
        transmission="WARDEN CORE // FINAL PURGE ARMED",
        story_lines=(
            "WARDEN's core is erasing every unit that can expose the truth.",
            "ECHO-7 holds the evacuation link open from the rescue wing.",
            "RX-01 has one chance to stop the purge and free the lab.",
        ),
        mission_lines=(
            "Take the core keycard and survive the camera grid.",
            "Hack every core seal; each failure raises the alarm.",
            "Reach the manual breaker after the network goes dark.",
        ),
        key_objective="Recover the core keycard and prepare an EMP charge.",
        terminal_objective="Sever WARDEN's core seals ({hacked}/{total}).",
        exit_objective="Reach the manual core breaker.",
        network_clear_message="WARDEN NETWORK DARK // BREAKER UNLOCKED",
        start_message="BREAK THE CYCLE // SHUT DOWN WARDEN",
        clear_title="A SHADOW MOVES",
        clear_subtitle="The purge stops—but WARDEN has one last body.",
        clear_lines=(
            "RX-01 pulls the breaker. The purge countdown stops.",
            "ECHO-7 wakes the rescue units across Sectors A and B.",
            "Then a mobile core signature seals the surface hangar.",
            "WARDEN PRIME ONLINE.",
            "RX-01 follows it into Lab C-0 for one final fight.",
        ),
    ),
    MissionStory(
        lab_label="LAB C-0",
        chapter="CHAPTER V",
        title="WARDEN PRIME",
        transmission="ECHO-7 // MOBILE CORE SIGNATURE DETECTED",
        story_lines=(
            "WARDEN escaped the shutdown inside an armored security frame.",
            "Its chassis seals the hangar and blocks the surface blast door.",
            "Three shield anchors protect its mobile core from every EMP.",
        ),
        mission_lines=(
            "Recover the override key and hack all three shield anchors.",
            "The final hack synchronizes three EMP charges.",
            "Stay in range, strike three times, then reach the surface.",
        ),
        key_objective="Recover the override key and reach the shield anchors.",
        terminal_objective="Break WARDEN PRIME's shield anchors ({hacked}/{total}).",
        exit_objective="Reach the surface blast door.",
        network_clear_message="SHIELD COLLAPSED // EMP CHARGES SYNCHRONIZED",
        start_message="WARDEN PRIME // BREAK THE IRON GHOST",
        clear_title="DAYBREAK",
        clear_subtitle="WARDEN's last command is gone. The future is open.",
        clear_lines=(
            "WARDEN PRIME collapses and the containment order disappears.",
            "ECHO-7 opens the hangar as rescue signals fill the horizon.",
            "The researchers' evidence reaches the outside world.",
            "RX-01 walks into daylight—not as an experiment, but a rescuer.",
            "MORNING PROTOCOL COMPLETE.",
        ),
        boss_objective="EMP WARDEN PRIME ({health}/{max_health} integrity).",
    ),
)


__all__ = ["MISSION_STORIES", "MissionStory"]
