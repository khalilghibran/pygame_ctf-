"""Robot Lab Escape executable entry point."""

from __future__ import annotations

from game import Game


def main() -> None:
    """Start the game application."""
    Game().run()


if __name__ == "__main__":
    main()
