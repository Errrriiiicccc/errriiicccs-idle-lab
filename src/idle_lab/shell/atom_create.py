"""Atom Create / Edit Deck mode — Phase 2 stub (no silent save)."""

from __future__ import annotations

from enum import Enum


class AtomCreatePhase(str, Enum):
    IDLE = "idle"
    CREATE = "create"
    EDIT = "edit"


def atom_create_prompt(*, phase: AtomCreatePhase | str, activate_key: str = "`") -> str:
    key = (activate_key or "`").strip() or "`"
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.CREATE:
        return (
            "Atom Create (skeleton)\n"
            "C = place click/drag/key/OCR · drag indicator later\n"
            "Save on exit needs a real persist path — not wired yet\n"
            f"Esc = leave Atom Create · {key} = Deactivate"
        )
    if kind is AtomCreatePhase.EDIT:
        return (
            "Atom Edit (skeleton)\n"
            "W/S = prev/next · R/F = reorder · event chords later\n"
            "Save on exit needs a real persist path — not wired yet\n"
            f"Esc = leave edit · {key} = Deactivate"
        )
    return (
        "Atom Create mode\n"
        "C = create · E = edit · Esc = back to menu\n"
        "No silent save — persist path not wired\n"
        f"{key} = Deactivate"
    )


def atom_create_legend(*, phase: AtomCreatePhase | str) -> str:
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.CREATE:
        return "ATOM CREATE · ESC = EXIT"
    if kind is AtomCreatePhase.EDIT:
        return "ATOM EDIT · W/S R/F · ESC"
    return "ATOM CREATE · C / E · ESC"
