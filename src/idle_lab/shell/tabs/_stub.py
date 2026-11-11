"""Shared placeholder pane for unwired Labs."""

from __future__ import annotations

import customtkinter as ctk


def build_stub_pane(parent, *, title: str, blurb: str) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=16, pady=16)
    ctk.CTkLabel(
        frame,
        text=title,
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(anchor="w", pady=(8, 4))
    ctk.CTkLabel(
        frame,
        text=blurb,
        text_color="#9AA4B2",
        wraplength=720,
        justify="left",
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        frame,
        text="not wired — Phase 0 skeleton",
        text_color="#E7C36A",
        font=ctk.CTkFont(size=13, weight="bold"),
        anchor="w",
    ).pack(anchor="w", pady=(16, 0))
    return frame
