"""Observation Lab panes — User + AI mission (left-rail leaves, not inner tabs)."""

from __future__ import annotations

import customtkinter as ctk

from idle_lab.feel_lab.themes import Look, default_look


def build_observation_user_pane(parent, *, look: Look | None = None, host_user=None):
    skin = look or default_look()
    root = ctk.CTkFrame(parent, fg_color=skin.bg)
    root.pack(fill="both", expand=True)

    ctk.CTkLabel(
        root,
        text="Observation Lab · User",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=skin.line,
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(12, 2))
    ctk.CTkLabel(
        root,
        text="Mark and rename-on-stop are cut. Stop capture with Deactivate (`).",
        text_color=skin.muted,
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(0, 8))

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_user is not None:
        host_user(host)
    else:
        _stub(
            host,
            skin,
            "User capture / review",
            "Catalog groups Today · Yesterday · Last 7 Days · The Past mount with the panel.",
        )
    return root


def build_observation_ai_pane(parent, *, look: Look | None = None, host_ai_mission=None):
    skin = look or default_look()
    root = ctk.CTkFrame(parent, fg_color=skin.bg)
    root.pack(fill="both", expand=True)

    ctk.CTkLabel(
        root,
        text="Observation Lab · AI mission",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=skin.line,
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(12, 2))
    ctk.CTkLabel(
        root,
        text="Start · Mission view · Results. Stop with Deactivate (`).",
        text_color=skin.muted,
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(0, 8))

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_ai_mission is not None:
        host_ai_mission(host)
    else:
        _stub(
            host,
            skin,
            "AI mission",
            "Start · Mission view · Results panes come from the missions panel.",
        )
    return root


def _stub(parent, skin: Look, title: str, blurb: str) -> None:
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.pack(fill="both", expand=True, padx=12, pady=12)
    ctk.CTkLabel(
        box, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=skin.line, anchor="w"
    ).pack(anchor="w")
    ctk.CTkLabel(
        box, text=blurb, text_color=skin.muted, wraplength=640, justify="left", anchor="w"
    ).pack(anchor="w", pady=(6, 0))
    ctk.CTkLabel(
        box,
        text="not wired — waiting for App host callback",
        text_color=skin.esc_pop,
        anchor="w",
    ).pack(anchor="w", pady=(12, 0))
