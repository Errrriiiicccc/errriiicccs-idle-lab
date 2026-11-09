"""CLI flags shared by launch and Restart."""

from __future__ import annotations

AUTO_ANCHOR_FLAG = "--auto-anchor"


def pop_auto_anchor_flag(argv: list[str]) -> tuple[list[str], bool]:
    """Return remaining argv and whether ``--auto-anchor`` was present."""

    remaining: list[str] = []
    auto_anchor = False
    for arg in argv:
        if arg == AUTO_ANCHOR_FLAG:
            auto_anchor = True
            continue
        remaining.append(arg)
    return remaining, auto_anchor


def restart_command(executable: str, *, auto_anchor: bool = True) -> list[str]:
    """Argv for relaunching Idle Lab (Restart / R)."""

    cmd = [executable, "-m", "idle_lab"]
    if auto_anchor:
        cmd.append(AUTO_ANCHOR_FLAG)
    return cmd
