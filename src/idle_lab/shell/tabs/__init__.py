"""Idle Lab tab inventory + Lab panes."""

from __future__ import annotations

from typing import Any, Callable

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
    on_start_live_overlay: Callable[[], None] | None = None,
    on_open_atom_create: Callable[[], None] | None = None,
    on_open_composer: Callable[[], None] | None = None,
    host_automations: Callable[[Any], None] | None = None,
    host_atom_pane: Callable[[Any], None] | None = None,
    on_goto_molecule_tab: Callable[[], None] | None = None,
    on_register_molecule_lab_root: Callable[[Any], None] | None = None,
    host_observation_user: Callable[[Any], None] | None = None,
    host_observation_ai: Callable[[Any], None] | None = None,
) -> dict[str, object]:
    frames: dict[str, object] = {}
    for name in IDLE_LAB_TABS:
        host = tabs.add(name)
        if name == "Info":
            frames[name] = build_info_tab(host, on_open_tab=on_open_tab)
        elif name == "Live Overlay Lab":
            frames[name] = build_lol_tab(
                host,
                on_start_live=on_start_live_overlay,
                on_open_atom_create=on_open_atom_create,
            )
        elif name == "Molecule Lab":
            frames[name] = build_molecule_lab_tab(
                host,
                on_open_atom_create=on_open_atom_create,
                on_open_composer=on_open_composer,
                host_automations=host_automations,
                host_atom_pane=host_atom_pane,
                on_goto_molecule_tab=on_goto_molecule_tab,
                on_register_root=on_register_molecule_lab_root,
            )
        else:
            frames[name] = build_observation_lab_tab(
                host,
                host_user=host_observation_user,
                host_ai_mission=host_observation_ai,
            )
    return frames


__all__ = [
    "DEFAULT_TAB",
    "IDLE_LAB_TABS",
    "mount_stub_tabs",
    "normalize_last_tab",
]
