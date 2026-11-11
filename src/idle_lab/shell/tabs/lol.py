"""Live Overlay Lab stub."""

from __future__ import annotations

from idle_lab.shell.tabs._stub import build_stub_pane


def build_lol_tab(parent):
    return build_stub_pane(
        parent,
        title="Live Overlay Lab (LOL)",
        blurb="Interactive target map + live object-map hands. Wiring comes after the shell skeleton.",
    )
