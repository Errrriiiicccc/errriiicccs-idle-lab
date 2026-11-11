"""Post-Deactivate resume handle (Phase 0 stub)."""

from __future__ import annotations

from enum import Enum


class ResumeChoice(str, Enum):
    CONTINUE = "continue"  # Activate again — stub label
    RESTART_WIPE = "restart_wipe"  # stub; not wired beyond status
    OPEN_IDLE_LAB = "open_idle_lab"  # Esc


def resume_prompt(*, activate_key: str) -> str:
    """Inactive-deck copy after Deactivate = Stop all."""

    key = (activate_key or "`").strip() or "`"
    return (
        f"Stopped.\n"
        f"[{key}] = continue (Activate) · R = restart-wipe (stub) · Esc = Idle Lab"
    )


def resolve_resume_escape(*, resume_handle: bool, deck_inactive: bool) -> bool:
    """True when Esc should open Idle Lab from the resume handle."""

    return bool(resume_handle and deck_inactive)
