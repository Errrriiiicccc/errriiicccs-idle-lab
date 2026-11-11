"""Idle Lab chrome helpers (shape-first). App remains the process owner."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.shell.tabs import mount_stub_tabs, normalize_last_tab


def build_tab_host(
    root,
    *,
    on_tab_changed: Callable[[], None],
    last_tab: str | None,
    on_open_tab: Callable[[str], None] | None = None,
) -> tuple[ctk.CTkTabview, str]:
    """Create the target tab strip and select Info / last tab."""

    tabs = ctk.CTkTabview(root, command=on_tab_changed)
    tabs.pack(fill="both", expand=True, padx=8, pady=(4, 0))
    mount_stub_tabs(tabs, on_open_tab=on_open_tab)
    selected = normalize_last_tab(last_tab)
    try:
        tabs.set(selected)
    except Exception:
        selected = "Info"
        tabs.set(selected)
    return tabs, selected
