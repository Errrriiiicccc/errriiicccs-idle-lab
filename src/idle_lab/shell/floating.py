"""Lightweight floating Lab windows opened from Flight Deck."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk


class FloatingLabWindow(ctk.CTkToplevel):
    """Sparse floating Lab — Esc owned by Deck mode; close button exits mode."""

    _deactivate_windows_window_header_manipulation = True

    def __init__(
        self,
        master,
        *,
        title: str,
        heading: str,
        blurb: str,
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("420x280")
        self.minsize(320, 200)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", on_close)
        self._on_close = on_close

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(
            frame,
            text=heading,
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            frame,
            text=blurb,
            text_color="#9AA4B2",
            wraplength=380,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(
            frame,
            text="not wired — Phase 1 floating skeleton",
            text_color="#E7C36A",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(anchor="w", pady=(16, 0))
        ctk.CTkButton(
            frame,
            text="Close (Esc)",
            width=120,
            command=on_close,
        ).pack(anchor="w", pady=(20, 0))

    def focus_float(self) -> None:
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass
