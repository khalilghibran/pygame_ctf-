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
    start_message: str
    clear_title: str
    clear_subtitle: str
    clear_lines: tuple[str, ...]


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
)


__all__ = ["MISSION_STORIES", "MissionStory"]
