"""Observation Lab stub — User + AI mission later."""

from __future__ import annotations

from idle_lab.shell.tabs._stub import build_stub_pane


def build_observation_lab_tab(parent):
    return build_stub_pane(
        parent,
        title="Observation Lab",
        blurb=(
            "User capture/review and AI mission panes land later. "
            "Mark and rename-on-stop are cut. Capture modes can link to Live Overlay Lab later."
        ),
    )
