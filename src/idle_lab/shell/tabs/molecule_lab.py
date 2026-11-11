"""Molecule Lab tab — Atom + Molecule panes (Phase 3 shape)."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk


def build_molecule_lab_tab(
    parent,
    *,
    on_open_atom_create: Callable[[], None] | None = None,
    on_open_composer: Callable[[], None] | None = None,
    host_automations=None,
):
    """host_automations: optional callback(parent_frame) that packs AutomationsPanel."""

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 4))
    ctk.CTkLabel(
        header,
        text="Molecule Lab",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(side="left")
    ctk.CTkLabel(
        header,
        text="Trial polish parked — skeleton honest",
        text_color="#E7C36A",
        anchor="e",
    ).pack(side="right")

    tabs = ctk.CTkTabview(root)
    tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    atom = tabs.add("Atom")
    molecule = tabs.add("Molecule")
    trial = tabs.add("Trial")

    # Atom
    atom_frame = ctk.CTkFrame(atom, fg_color="transparent")
    atom_frame.pack(fill="both", expand=True, padx=12, pady=12)
    ctk.CTkLabel(
        atom_frame,
        text="Atom library + create",
        font=ctk.CTkFont(size=16, weight="bold"),
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        atom_frame,
        text="Open Atom Create on the Flight Deck (shared overlay primitives). Save only when a persist path is real.",
        text_color="#9AA4B2",
        wraplength=640,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(4, 10))
    ctk.CTkButton(
        atom_frame,
        text="Open Atom Create (Deck)",
        width=180,
        command=(on_open_atom_create or (lambda: None)),
        state="normal" if on_open_atom_create else "disabled",
    ).pack(anchor="w")

    # Molecule
    mol_frame = ctk.CTkFrame(molecule, fg_color="transparent")
    mol_frame.pack(fill="both", expand=True, padx=8, pady=8)
    toolbar = ctk.CTkFrame(mol_frame, fg_color="transparent")
    toolbar.pack(fill="x", pady=(0, 6))
    ctk.CTkButton(
        toolbar,
        text="Open flowing composer",
        width=160,
        command=(on_open_composer or (lambda: None)),
        state="normal" if on_open_composer else "disabled",
    ).pack(side="left")
    ctk.CTkLabel(
        toolbar,
        text="Start-all-enabled is cut · use explicit packs",
        text_color="#7E8796",
    ).pack(side="left", padx=(12, 0))
    panel_host = ctk.CTkFrame(mol_frame, fg_color="transparent")
    panel_host.pack(fill="both", expand=True)
    if host_automations is not None:
        host_automations(panel_host)
    else:
        ctk.CTkLabel(
            panel_host,
            text="Automations panel mounts here when App wires Molecule Lab.",
            text_color="#9AA4B2",
        ).pack(anchor="w", pady=12)

    # Trial (parked)
    trial_frame = ctk.CTkFrame(trial, fg_color="transparent")
    trial_frame.pack(fill="both", expand=True, padx=12, pady=12)
    ctk.CTkLabel(
        trial_frame,
        text="Trial",
        font=ctk.CTkFont(size=16, weight="bold"),
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        trial_frame,
        text="not wired — Trial ↔ creator IA polish is parked (S42).",
        text_color="#E7C36A",
        anchor="w",
    ).pack(anchor="w", pady=(8, 0))
    return root
