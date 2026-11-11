"""Observation Lab — User + AI mission tabs (Phase 4)."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk


def build_observation_lab_tab(
    parent,
    *,
    host_user=None,
    host_ai_mission=None,
):
    """host_*: optional callback(parent_frame) packing ScreenMapPanel / AiBatchPanel."""

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True)

    ctk.CTkLabel(
        root,
        text="Observation Lab",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(12, 2))
    ctk.CTkLabel(
        root,
        text="Mark and rename-on-stop are cut. Stop capture with Deactivate (`).",
        text_color="#9AA4B2",
        anchor="w",
    ).pack(anchor="w", padx=12, pady=(0, 8))

    tabs = ctk.CTkTabview(root)
    tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    user = tabs.add("User")
    mission = tabs.add("AI mission")

    user_host = ctk.CTkFrame(user, fg_color="transparent")
    user_host.pack(fill="both", expand=True)
    if host_user is not None:
        host_user(user_host)
    else:
        _stub(
            user_host,
            "User capture / review",
            "Catalog groups Today · Yesterday · Last 7 Days · The Past mount with the panel.",
        )

    mission_host = ctk.CTkFrame(mission, fg_color="transparent")
    mission_host.pack(fill="both", expand=True)
    if host_ai_mission is not None:
        host_ai_mission(mission_host)
    else:
        _stub(
            mission_host,
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
