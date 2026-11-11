"""Idle Lab tab inventory + stub panes."""

from __future__ import annotations

from typing import Callable

from idle_lab.shell.tabs.info import build_info_tab
from idle_lab.shell.tabs.lol import build_lol_tab
from idle_lab.shell.tabs.molecule_lab import build_molecule_lab_tab
from idle_lab.shell.tabs.observation_lab import build_observation_lab_tab

IDLE_LAB_TABS: tuple[str, ...] = (
    "Info",
    "Live Overlay Lab",
    "Molecule Lab",
    "Observation Lab",
)

DEFAULT_TAB = "Info"


def normalize_last_tab(raw: str | None) -> str:
    name = str(raw or "").strip()
    if name in IDLE_LAB_TABS:
        return name
    # Legacy mega-tab / short names → current operator labels.
    legacy = {
        "Bench": "Molecule Lab",
        "Observe": "Observation Lab",
        "Missions": "Observation Lab",
        "Loops": "Molecule Lab",
        "Clicker": "Molecule Lab",
        "Automations": "Molecule Lab",
        "Screen Map": "Observation Lab",
        "AI Batches": "Observation Lab",
        "LOL": "Live Overlay Lab",
        "Live Overlay Lab (LOL)": "Live Overlay Lab",
    }
    return legacy.get(name, DEFAULT_TAB)


def mount_stub_tabs(
    tabs,
    *,
    on_open_tab: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Add target tabs and fill panes. Info gets real outline; Labs stay stubs."""

    frames: dict[str, object] = {}
    for name in IDLE_LAB_TABS:
        host = tabs.add(name)
        if name == "Info":
            frames[name] = build_info_tab(host, on_open_tab=on_open_tab)
        elif name == "Live Overlay Lab":
            frames[name] = build_lol_tab(host)
        elif name == "Molecule Lab":
            frames[name] = build_molecule_lab_tab(host)
        else:
            frames[name] = build_observation_lab_tab(host)
    return frames


__all__ = [
    "DEFAULT_TAB",
    "IDLE_LAB_TABS",
    "mount_stub_tabs",
    "normalize_last_tab",
]
