"""Info tab stub — nested docs land in Phase 1."""

from __future__ import annotations

from idle_lab.shell.tabs._stub import build_stub_pane


def build_info_tab(parent):
    return build_stub_pane(
        parent,
        title="Info",
        blurb=(
            "Verbose onboarding and Lab checklists will live here. "
            "For now this is the factory landing tab."
        ),
    )
