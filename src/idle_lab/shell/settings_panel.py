"""Settings slice — boot preference + Activate-key remap (Phase 1)."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.flight_deck.keys import vk_label

BOOT_IDLE_LAB = "idle_lab"
BOOT_FLIGHT_DECK = "flight_deck"

BOOT_LABELS = {
    BOOT_IDLE_LAB: "Idle Lab (factory)",
    BOOT_FLIGHT_DECK: "Flight Deck",
}
BOOT_FROM_LABEL = {label: key for key, label in BOOT_LABELS.items()}


def normalize_boot_surface(raw: str | None) -> str:
    value = str(raw or "").strip().lower().replace(" ", "_")
    if value in {BOOT_IDLE_LAB, "lab", "idle"}:
        return BOOT_IDLE_LAB
    if value in {BOOT_FLIGHT_DECK, "deck", "flight_deck", "flightdeck"}:
        return BOOT_FLIGHT_DECK
    return BOOT_IDLE_LAB


def build_settings_body(
    parent,
    *,
    boot_surface: str,
    expand_vk: int,
    on_boot_change: Callable[[str], None],
    on_begin_remap: Callable[[], None],
) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=12, pady=12)

    ctk.CTkLabel(
        frame,
        text="Settings",
        font=ctk.CTkFont(size=20, weight="bold"),
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        frame,
        text="Phase 1 slice — boot surface and Activate key. More later.",
        text_color="#9AA4B2",
        anchor="w",
    ).pack(anchor="w", pady=(4, 12))

    boot_row = ctk.CTkFrame(frame, fg_color="transparent")
    boot_row.pack(fill="x", pady=(0, 10))
    ctk.CTkLabel(boot_row, text="Boot surface", width=120, anchor="w").pack(side="left")
    boot_menu = ctk.CTkOptionMenu(
        boot_row,
        values=list(BOOT_LABELS.values()),
        width=180,
        command=lambda label: on_boot_change(BOOT_FROM_LABEL.get(label, BOOT_IDLE_LAB)),
    )
    boot_menu.set(BOOT_LABELS.get(normalize_boot_surface(boot_surface), BOOT_LABELS[BOOT_IDLE_LAB]))
    boot_menu.pack(side="left")

    key_row = ctk.CTkFrame(frame, fg_color="transparent")
    key_row.pack(fill="x", pady=(0, 10))
    ctk.CTkLabel(key_row, text="Activate key", width=120, anchor="w").pack(side="left")
    key_label = ctk.CTkLabel(
        key_row,
        text=vk_label(expand_vk),
        width=48,
        anchor="w",
        text_color="#8EE0C2",
        font=ctk.CTkFont(weight="bold"),
    )
    key_label.pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        key_row,
        text="Remap…",
        width=88,
        command=on_begin_remap,
    ).pack(side="left")

    ctk.CTkLabel(
        frame,
        text="Remap listens for the next key (Esc cancels). Saved per anchor when one is set.",
        text_color="#7E8796",
        wraplength=420,
        justify="left",
        anchor="w",
    ).pack(anchor="w", pady=(8, 0))
    return frame
