"""Small comment bubble + dialog for hierarchical lab notes."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk


def make_comment_button(
    master,
    *,
    has_notes: bool,
    command: Callable[[], None],
    width: int = 36,
) -> ctk.CTkButton:
    """Chat-bubble style button; accent when notes exist."""

    return ctk.CTkButton(
        master,
        text="Note",
        width=width if width >= 44 else 44,
        height=28,
        fg_color="#1F6AA5" if has_notes else "#2A3140",
        hover_color="#3A4558",
        command=command,
    )


def open_comment_dialog(
    master,
    *,
    title: str,
    object_path: str,
    initial: str,
    on_save: Callable[[str], None],
) -> None:
    """Modal-ish note editor. Saves on Save; Escape / Close discards unsaved edits."""

    dialog = ctk.CTkToplevel(master)
    dialog.title(title)
    dialog.geometry("520x320")
    dialog.transient(master)
    dialog.grab_set()
    dialog.focus_force()

    ctk.CTkLabel(dialog, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(
        anchor="w", padx=14, pady=(12, 2)
    )
    ctk.CTkLabel(
        dialog,
        text=object_path,
        anchor="w",
        text_color="#9AA4B2",
        font=ctk.CTkFont(size=11),
    ).pack(fill="x", padx=14, pady=(0, 8))

    box = ctk.CTkTextbox(dialog, wrap="word")
    box.pack(fill="both", expand=True, padx=14, pady=(0, 8))
    if initial:
        box.insert("1.0", initial)

    def save() -> None:
        on_save(box.get("1.0", "end-1c"))
        dialog.grab_release()
        dialog.destroy()

    def cancel() -> None:
        dialog.grab_release()
        dialog.destroy()

    buttons = ctk.CTkFrame(dialog, fg_color="transparent")
    buttons.pack(fill="x", padx=14, pady=(0, 12))
    ctk.CTkButton(buttons, text="Save", width=90, command=save).pack(side="right")
    ctk.CTkButton(
        buttons,
        text="Cancel",
        width=90,
        fg_color="#2A3140",
        hover_color="#3A4558",
        command=cancel,
    ).pack(side="right", padx=(0, 8))
    dialog.bind("<Escape>", lambda _e: cancel())
