"""Operator shell — Idle Lab ↔ Flight Deck surfaces (shape-first)."""

from __future__ import annotations

from idle_lab.shell.surfaces import Surface, SurfaceKind, can_show_idle_lab, hotkeys_allowed
from idle_lab.shell.tabs import IDLE_LAB_TABS, normalize_last_tab

__all__ = [
    "IDLE_LAB_TABS",
    "Surface",
    "SurfaceKind",
    "can_show_idle_lab",
    "hotkeys_allowed",
    "normalize_last_tab",
]
