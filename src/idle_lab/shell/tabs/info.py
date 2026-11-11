"""Info tab — nested accordion docs with Lab jump links."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.shell.info_content import INFO_OUTLINE, InfoSection


def build_info_tab(parent, *, on_open_tab: Callable[[str], None] | None = None):
    outer = ctk.CTkScrollableFrame(parent, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=8, pady=8)
    ctk.CTkLabel(
        outer,
        text="Info",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(anchor="w", padx=8, pady=(4, 2))
    ctk.CTkLabel(
        outer,
        text="Travel the outline — checklists and links jump to Labs. Live status stays in chrome.",
        text_color="#9AA4B2",
        wraplength=720,
        justify="left",
        anchor="w",
    ).pack(anchor="w", padx=8, pady=(0, 10))

    for section in INFO_OUTLINE:
        _mount_section(outer, section, on_open_tab=on_open_tab, depth=0)
    return outer


def _mount_section(
    parent,
    section: InfoSection,
    *,
    on_open_tab: Callable[[str], None] | None,
    depth: int,
) -> None:
    card = ctk.CTkFrame(parent, corner_radius=8)
    card.pack(fill="x", padx=8 + depth * 12, pady=4)

    body_host = ctk.CTkFrame(card, fg_color="transparent")
    open_state = {"open": depth == 0}

    def toggle() -> None:
        open_state["open"] = not open_state["open"]
        if open_state["open"]:
            body_host.pack(fill="x", padx=10, pady=(0, 10))
            toggle_btn.configure(text="▼")
        else:
            body_host.pack_forget()
            toggle_btn.configure(text="▶")

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=8, pady=6)
    toggle_btn = ctk.CTkButton(
        header,
        text="▼" if open_state["open"] else "▶",
        width=28,
        height=28,
        fg_color="transparent",
        hover_color="#2A3140",
        command=toggle,
    )
    toggle_btn.pack(side="left")
    ctk.CTkLabel(
        header,
        text=section.title,
        font=ctk.CTkFont(size=15 if depth == 0 else 13, weight="bold"),
        anchor="w",
    ).pack(side="left", padx=(4, 0))

    ctk.CTkLabel(
        body_host,
        text=section.body,
        text_color="#C5CDD8",
        wraplength=680 - depth * 20,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(0, 6))

    if section.checklist:
        ctk.CTkLabel(
            body_host,
            text="Checklist",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#A8B4C4",
            anchor="w",
        ).pack(anchor="w")
        for item in section.checklist:
            ctk.CTkLabel(
                body_host,
                text=f"☐  {item}",
                text_color="#9AA4B2",
                wraplength=660 - depth * 20,
                justify="left",
                anchor="w",
            ).pack(anchor="w", pady=1)

    if section.links and on_open_tab is not None:
        link_row = ctk.CTkFrame(body_host, fg_color="transparent")
        link_row.pack(anchor="w", pady=(8, 0))
        for link in section.links:
            ctk.CTkButton(
                link_row,
                text=link.label,
                width=160,
                height=28,
                fg_color="#1E3A4A",
                hover_color="#2A5568",
                command=lambda tab=link.tab: on_open_tab(tab),
            ).pack(side="left", padx=(0, 8))

    for child in section.children:
        _mount_section(body_host, child, on_open_tab=on_open_tab, depth=depth + 1)

    if open_state["open"]:
        body_host.pack(fill="x", padx=10, pady=(0, 10))
    else:
        body_host.pack_forget()
