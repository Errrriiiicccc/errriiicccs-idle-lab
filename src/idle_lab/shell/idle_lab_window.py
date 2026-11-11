"""Idle Lab chrome helpers (shape-first). App remains the process owner."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.shell.tabs import mount_stub_tabs, normalize_last_tab


def build_live_status_stub(parent) -> ctk.CTkLabel:
    """Chrome live-status strip — empty stub OK for Phase 0."""

    label = ctk.CTkLabel(
        parent,
        text="Status: idle (stub)",
        anchor="w",
        text_color="#A8B4C4",
        font=ctk.CTkFont(size=11),
    )
    return label


def build_tab_host(
    root,
    *,
    on_tab_changed: Callable[[], None],
    last_tab: str | None,
) -> tuple[ctk.CTkTabview, str]:
    """Create the target tab strip and select Info / last tab."""

    tabs = ctk.CTkTabview(root, command=on_tab_changed)
    tabs.pack(fill="both", expand=True, padx=8, pady=(4, 0))
    mount_stub_tabs(tabs)
    selected = normalize_last_tab(last_tab)
    try:
        tabs.set(selected)
    except Exception:
        selected = "Info"
        tabs.set(selected)
    return tabs, selected
