"""Idle Lab tab inventory + stub panes."""

from __future__ import annotations

from idle_lab.shell.tabs.info import build_info_tab
from idle_lab.shell.tabs.lol import build_lol_tab
from idle_lab.shell.tabs.molecule_lab import build_molecule_lab_tab
from idle_lab.shell.tabs.observation_lab import build_observation_lab_tab

IDLE_LAB_TABS: tuple[str, ...] = (
    "Info",
    "LOL",
    "Molecule Lab",
    "Observation Lab",
)

DEFAULT_TAB = "Info"


def normalize_last_tab(raw: str | None) -> str:
    name = str(raw or "").strip()
    if name in IDLE_LAB_TABS:
        return name
    # Legacy mega-tab names → closest Lab stub.
    legacy = {
        "Bench": "Molecule Lab",
        "Observe": "Observation Lab",
        "Missions": "Observation Lab",
        "Loops": "Molecule Lab",
        "Clicker": "Molecule Lab",
        "Automations": "Molecule Lab",
        "Screen Map": "Observation Lab",
        "AI Batches": "Observation Lab",
        "Live Overlay Lab": "LOL",
        "Live Overlay Lab (LOL)": "LOL",
    }
    return legacy.get(name, DEFAULT_TAB)


def mount_stub_tabs(tabs) -> dict[str, object]:
    """Add target tabs and fill with placeholder panes. Returns frame map."""

    frames: dict[str, object] = {}
    builders = {
        "Info": build_info_tab,
        "LOL": build_lol_tab,
        "Molecule Lab": build_molecule_lab_tab,
        "Observation Lab": build_observation_lab_tab,
    }
    for name in IDLE_LAB_TABS:
        host = tabs.add(name)
        frames[name] = builders[name](host)
    return frames


__all__ = [
    "DEFAULT_TAB",
    "IDLE_LAB_TABS",
    "mount_stub_tabs",
    "normalize_last_tab",
]
