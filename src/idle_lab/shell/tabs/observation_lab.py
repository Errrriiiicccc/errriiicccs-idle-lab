"""Observation Lab panes — User + AI mission (left-rail leaves, not inner tabs)."""

from __future__ import annotations

import customtkinter as ctk


def build_observation_user_pane(parent, *, host_user=None):
    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True)

    ctk.CTkLabel(
        root,
        text="Observation Lab · User",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(12, 2))
    ctk.CTkLabel(
        root,
        text="Mark and rename-on-stop are cut. Stop capture with Deactivate (`).",
        text_color="#9AA4B2",
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(0, 8))

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_user is not None:
        host_user(host)
    else:
        _stub(
            host,
            "User capture / review",
            "Catalog groups Today · Yesterday · Last 7 Days · The Past mount with the panel.",
        )
    return root


def build_observation_ai_pane(parent, *, host_ai_mission=None):
    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True)

    ctk.CTkLabel(
        root,
        text="Observation Lab · AI mission",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(12, 2))
    ctk.CTkLabel(
        root,
        text="Start · Mission view · Results. Stop with Deactivate (`).",
        text_color="#9AA4B2",
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(0, 8))

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_ai_mission is not None:
        host_ai_mission(host)
    else:
        _stub(
            host,
            "AI mission",
            "Start · Mission view · Results panes come from the missions panel.",
        )
    return root


def _stub(parent, title: str, blurb: str) -> None:
    box = ctk.CTkFrame(parent, fg_color="transparent")
    box.pack(fill="both", expand=True, padx=12, pady=12)
    ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=16, weight="bold"), anchor="w").pack(
        anchor="w"
    )
    ctk.CTkLabel(box, text=blurb, text_color="#9AA4B2", wraplength=640, justify="left", anchor="w").pack(
        anchor="w", pady=(6, 0)
    )
    ctk.CTkLabel(
        box,
        text="not wired — waiting for App host callback",
        text_color="#E7C36A",
        anchor="w",
    ).pack(anchor="w", pady=(12, 0))
