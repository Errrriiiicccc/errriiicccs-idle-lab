"""Idle Lab chrome helpers (shape-first). App remains the process owner."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from idle_lab.shell.tabs import mount_stub_tabs, normalize_last_tab


def build_tab_host(
    root,
    *,
    on_tab_changed: Callable[[], None],
    last_tab: str | None,
    on_open_tab: Callable[[str], None] | None = None,
    on_start_live_overlay: Callable[[], None] | None = None,
    on_open_atom_create: Callable[[], None] | None = None,
    on_open_composer: Callable[[], None] | None = None,
    host_automations: Callable[[Any], None] | None = None,
    host_composer: Callable[[Any], None] | None = None,
    host_atom_pane: Callable[[Any], None] | None = None,
    on_goto_molecule_tab: Callable[[], None] | None = None,
    on_goto_trial_tab: Callable[[], None] | None = None,
    on_register_molecule_lab_root: Callable[[Any], None] | None = None,
    host_observation_user: Callable[[Any], None] | None = None,
    host_observation_ai: Callable[[Any], None] | None = None,
) -> tuple[ctk.CTkTabview, str]:
    tabs = ctk.CTkTabview(root, command=on_tab_changed)
    tabs.pack(fill="both", expand=True, padx=8, pady=(4, 0))
    mount_stub_tabs(
        tabs,
        on_open_tab=on_open_tab,
        on_start_live_overlay=on_start_live_overlay,
        on_open_atom_create=on_open_atom_create,
        on_open_composer=on_open_composer,
        host_automations=host_automations,
        host_composer=host_composer,
        host_atom_pane=host_atom_pane,
        on_goto_molecule_tab=on_goto_molecule_tab,
        on_goto_trial_tab=on_goto_trial_tab,
        on_register_molecule_lab_root=on_register_molecule_lab_root,
        host_observation_user=host_observation_user,
        host_observation_ai=host_observation_ai,
    )
    selected = normalize_last_tab(last_tab)
    try:
        tabs.set(selected)
    except Exception:
        selected = "Info"
        tabs.set(selected)
    return tabs, selected
