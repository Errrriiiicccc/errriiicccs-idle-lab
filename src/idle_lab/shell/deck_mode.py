"""Flight Deck mode abandon — menu letters drop when a Lab mode is open."""

from __future__ import annotations

from enum import Enum


class DeckMode(str, Enum):
    MENU = "menu"
    LOL = "lol"
    MOLECULE_LAB = "molecule_lab"
    OBSERVATION_LAB = "observation_lab"
    SETTINGS = "settings"
    ATOM_CREATE = "atom_create"


def mode_abandons_menu(mode: DeckMode | str) -> bool:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    return kind is not DeckMode.MENU


def mode_prompt(mode: DeckMode | str, *, activate_key: str = "`") -> str:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    key = (activate_key or "`").strip() or "`"
    if kind is DeckMode.LOL:
        return (
            "Live Overlay Lab\n"
            f"Esc = exit → Deck menu · {key} = pause / resume\n"
            "Hold D = describe · Anchor required"
        )
    if kind is DeckMode.MOLECULE_LAB:
        return (
            "Molecule Lab (floating composer)\n"
            f"Esc = stop run or close → Deck menu · {key} = Deactivate\n"
            "Type freely — deck letter map paused"
        )
    if kind is DeckMode.OBSERVATION_LAB:
        return (
            "Observation Lab\n"
            f"Esc = stop capture or close → Deck menu · {key} = Deactivate\n"
            "Full User + AI mission panes live in Idle Lab"
        )
    if kind is DeckMode.SETTINGS:
        return (
            "Settings\n"
            f"Esc = back to Deck menu · {key} = Deactivate\n"
            "Boot preference + Activate key (applies on Restart)."
        )
    if kind is DeckMode.ATOM_CREATE:
        from idle_lab.shell.atom_create import atom_create_prompt

        return atom_create_prompt(phase="create", activate_key=key)
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
    if kind is DeckMode.ATOM_CREATE:
        from idle_lab.shell.atom_create import atom_create_legend

        return atom_create_legend(phase="idle")
    return "ESC"


def mode_display_name(mode: DeckMode | str) -> str:
    kind = mode if isinstance(mode, DeckMode) else DeckMode(str(mode))
    return {
        DeckMode.MENU: "Menu",
        DeckMode.LOL: "Live Overlay Lab",
        DeckMode.MOLECULE_LAB: "Molecule Lab",
        DeckMode.OBSERVATION_LAB: "Observation Lab",
        DeckMode.SETTINGS: "Settings",
        DeckMode.ATOM_CREATE: "Atom Create",
    }.get(kind, str(kind))
