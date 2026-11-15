"""Live Overlay Lab tab — map list + live start (Phase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from idle_lab.feel_lab.themes import Look, default_look
from idle_lab.presets import project_root
from idle_lab.shell.paint import dormant_button_kwargs, primary_button_kwargs


def build_lol_tab(
    parent,
    *,
    look: Look | None = None,
    on_start_live: Callable[[], None] | None = None,
    on_open_atom_create: Callable[[], None] | None = None,
):
    skin = look or default_look()
    frame = ctk.CTkFrame(parent, fg_color=skin.bg)
    frame.pack(fill="both", expand=True, padx=12, pady=12)

    ctk.CTkLabel(
        frame,
        text="Live Overlay Lab",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=skin.line,
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        frame,
        text="Interactive target map + live object-map hands. Shared overlay primitives with Atom Create.",
        text_color=skin.muted,
        wraplength=720,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(4, 10))

    toolbar = ctk.CTkFrame(frame, fg_color="transparent")
    toolbar.pack(fill="x", pady=(0, 8))
    ctk.CTkButton(
        toolbar,
        text="Start live",
        width=120,
        command=(on_start_live or (lambda: None)),
        state="normal" if on_start_live else "disabled",
        **primary_button_kwargs(skin),
    ).pack(side="left")
    ctk.CTkButton(
        toolbar,
        text="Create Atom",
        width=120,
        command=(on_open_atom_create or (lambda: None)),
        state="normal" if on_open_atom_create else "disabled",
        **dormant_button_kwargs(skin),
    ).pack(side="left", padx=(8, 0))
    ctk.CTkLabel(
        toolbar,
        text="Anchor required · Start live collapses Lab · Esc expands",
        text_color=skin.muted,
        anchor="w",
    ).pack(side="left", padx=(12, 0))

    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.pack(fill="both", expand=True)
    left = ctk.CTkScrollableFrame(
        body,
        width=280,
        fg_color=skin.panel,
        border_width=1 if skin.style == "type" else 0,
        border_color=skin.desc_border,
    )
    left.pack(side="left", fill="y", padx=(8, 4), pady=8)
    right = ctk.CTkFrame(
        body,
        fg_color=skin.panel,
        border_width=1 if skin.style == "type" else 0,
        border_color=skin.desc_border,
    )
    right.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=8)

    ctk.CTkLabel(
        left, text="Object maps", font=ctk.CTkFont(weight="bold"), text_color=skin.line, anchor="w"
    ).pack(anchor="w", pady=(0, 6), padx=8)
    maps_dir = project_root() / "automations" / "maps"
    paths = sorted(maps_dir.glob("*.objects.json")) if maps_dir.is_dir() else []
    highlight = ctk.CTkLabel(
        right,
        text="Select a map — miniature highlight later.",
        text_color=skin.muted,
        wraplength=400,
        justify="left",
        anchor="nw",
    )
    highlight.pack(anchor="nw", fill="both", expand=True, padx=10, pady=10)

    def select(path: Path) -> None:
        highlight.configure(
            text=(
                f"Map: {path.name}\n\n"
                "Miniature follow-highlight is not wired yet.\n"
                "Start live uses the active playbook / object map on the anchored window."
            )
        )

    if not paths:
        ctk.CTkLabel(left, text="(no *.objects.json yet)", text_color=skin.muted).pack(
            anchor="w", padx=8
        )
    else:
        for path in paths:
            ctk.CTkButton(
                left,
                text=path.stem.replace(".objects", ""),
                anchor="w",
                fg_color="transparent",
                hover_color=skin.live_hover,
                text_color=skin.line,
                command=lambda p=path: select(p),
            ).pack(fill="x", pady=1, padx=4)
        select(paths[0])

    ctk.CTkLabel(
        frame,
        text="Hotkey remap + conflict warnings: stub — Phase 2 map chrome only.",
        text_color=skin.esc_pop,
        anchor="w",
    ).pack(anchor="w", pady=(8, 0))
    return frame
