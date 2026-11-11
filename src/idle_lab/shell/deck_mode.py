"""Flight Deck mode abandon — menu letters drop when a Lab mode is open."""

from __future__ import annotations

from enum import Enum


class DeckMode(str, Enum):
    MENU = "menu"
    LOL = "lol"
    MOLECULE_LAB = "molecule_lab"
    OBSERVATION_LAB = "observation_lab"
    SETTINGS = "settings"


def mode_abandons_menu(mode: DeckMode | str) -> bool:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    return kind is not DeckMode.MENU


def mode_prompt(mode: DeckMode | str, *, activate_key: str = "`") -> str:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    key = (activate_key or "`").strip() or "`"
    if kind is DeckMode.LOL:
        return (
            "Live Overlay Lab mode (skeleton)\n"
            f"Esc = back to Deck menu · {key} = Deactivate\n"
            "Live overlay wiring lands in Phase 2 — not wired yet."
        )
    if kind is DeckMode.MOLECULE_LAB:
        return (
            "Molecule Lab floating (skeleton)\n"
            f"Esc = close float → Deck menu · {key} = Deactivate\n"
            "Full composer wiring comes later — not wired yet."
        )
    if kind is DeckMode.OBSERVATION_LAB:
        return (
            "Observation Lab floating (skeleton)\n"
            f"Esc = close float → Deck menu · {key} = Deactivate\n"
            "User + AI mission panes later — not wired yet."
        )
    if kind is DeckMode.SETTINGS:
        return (
            "Settings\n"
            f"Esc = back to Deck menu · {key} = Deactivate\n"
            "Boot preference + Activate key."
        )
    return ""


def mode_legend(mode: DeckMode | str) -> str:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    if kind is DeckMode.MENU:
        return "MENU"
    if kind is DeckMode.LOL:
        return "ESC = EXIT LIVE OVERLAY LAB"
    if kind is DeckMode.MOLECULE_LAB:
        return "ESC = CLOSE MOLECULE LAB"
    if kind is DeckMode.OBSERVATION_LAB:
        return "ESC = CLOSE OBSERVATION LAB"
    if kind is DeckMode.SETTINGS:
        return "ESC = CLOSE SETTINGS"
    return "ESC"


def mode_display_name(mode: DeckMode | str) -> str:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    return {
        DeckMode.MENU: "Menu",
        DeckMode.LOL: "Live Overlay Lab",
        DeckMode.MOLECULE_LAB: "Molecule Lab",
        DeckMode.OBSERVATION_LAB: "Observation Lab",
        DeckMode.SETTINGS: "Settings",
    }.get(kind, str(kind))
