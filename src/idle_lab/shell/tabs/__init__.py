"""Idle Lab tab inventory + Lab panes."""

from __future__ import annotations

from idle_lab.shell.nav import (
    DEFAULT_PATH,
    IDLE_LAB_TABS,
    LAB_BRANCHES,
    all_desk_paths,
    default_path_for_root,
    join_path,
    normalize_last_tab,
    normalize_nav_path,
    path_leaf,
    path_root,
)
from idle_lab.shell.tabs.info import build_info_tab
from idle_lab.shell.tabs.lol import build_lol_tab
from idle_lab.shell.tabs.molecule_lab import (
    AtomLabPane,
    build_molecule_atom_pane,
    build_molecule_compose_pane,
    build_molecule_trial_pane,
)
from idle_lab.shell.tabs.observation_lab import (
    build_observation_ai_pane,
    build_observation_user_pane,
)

__all__ = [
    "AtomLabPane",
    "DEFAULT_PATH",
    "IDLE_LAB_TABS",
    "LAB_BRANCHES",
    "all_desk_paths",
    "build_info_tab",
    "build_lol_tab",
    "build_molecule_atom_pane",
    "build_molecule_compose_pane",
    "build_molecule_trial_pane",
    "build_observation_ai_pane",
    "build_observation_user_pane",
    "default_path_for_root",
    "join_path",
    "normalize_last_tab",
    "normalize_nav_path",
    "path_leaf",
    "path_root",
]
