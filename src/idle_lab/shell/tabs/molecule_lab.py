"""Molecule Lab stub — Atom + Molecule later."""

from __future__ import annotations

from idle_lab.shell.tabs._stub import build_stub_pane


def build_molecule_lab_tab(parent):
    return build_stub_pane(
        parent,
        title="Molecule Lab",
        blurb="Atom create/edit and molecule compose will replace the old Loops/Bench surfaces here.",
    )
