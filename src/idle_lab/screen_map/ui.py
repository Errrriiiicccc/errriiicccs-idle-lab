"""Screen Map tab UI."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk


class ScreenMapPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        on_start_batch: Callable[[], None],
        on_end_batch: Callable[[], None],
        on_open_folder: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_start_batch = on_start_batch
        self.on_end_batch = on_end_batch
        self.on_open_folder = on_open_folder
        self._build()

    def _build(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(toolbar, text="Screen Map", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.open_button = ctk.CTkButton(toolbar, text="Open folder", width=110, command=self.on_open_folder)
        self.open_button.pack(side="right", padx=(6, 0))
        self.end_button = ctk.CTkButton(toolbar, text="End batch", width=100, command=self.on_end_batch)
        self.end_button.pack(side="right", padx=(6, 0))
        self.start_button = ctk.CTkButton(toolbar, text="Start batch…", width=120, command=self.on_start_batch)
        self.start_button.pack(side="right")

        status = ctk.CTkFrame(self)
        status.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(status, text="Status", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 2)
        )
        self.mode_label = ctk.CTkLabel(status, text="Screenshot mode: OFF", anchor="w")
        self.mode_label.pack(fill="x", padx=10)
        self.path_label = ctk.CTkLabel(status, text="Batch: (none)", anchor="w", wraplength=900)
        self.path_label.pack(fill="x", padx=10, pady=(2, 0))
        self.count_label = ctk.CTkLabel(status, text="Shots: 0", anchor="w")
        self.count_label.pack(fill="x", padx=10, pady=(2, 10))

        help_frame = ctk.CTkFrame(self)
        help_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(
            help_frame,
            text=(
                "Anchor the emulator on the Clicker tab first. Start a batch, then press Space to title "
                "and capture each screen. Esc cancels an open title dialog; Esc again ends the batch."
            ),
            anchor="w",
            justify="left",
            wraplength=900,
            text_color="#9AA4B2",
        ).pack(fill="x", padx=10, pady=10)

        shots = ctk.CTkFrame(self)
        shots.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        ctk.CTkLabel(shots, text="Recent shots", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 2)
        )
        self.shot_list = ctk.CTkScrollableFrame(shots, height=320)
        self.shot_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._empty = ctk.CTkLabel(self.shot_list, text="No shots yet.", text_color="#9AA4B2")
        self._empty.pack(anchor="w", padx=4)
        self.set_idle()

    def set_idle(self) -> None:
        self.mode_label.configure(text="Screenshot mode: OFF")
        self.path_label.configure(text="Batch: (none)")
        self.count_label.configure(text="Shots: 0")
        self.start_button.configure(state="normal")
        self.end_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self._render_titles([])

    def set_active(self, folder: Path, titles: list[str]) -> None:
        self.mode_label.configure(text="Screenshot mode: ON")
        self.path_label.configure(text=f"Batch: {folder}")
        self.count_label.configure(text=f"Shots: {len(titles)}")
        self.start_button.configure(state="disabled")
        self.end_button.configure(state="normal")
        self.open_button.configure(state="normal")
        self._render_titles(titles)

    def _render_titles(self, titles: list[str]) -> None:
        for child in self.shot_list.winfo_children():
            child.destroy()
        if not titles:
            ctk.CTkLabel(self.shot_list, text="No shots yet.", text_color="#9AA4B2").pack(anchor="w", padx=4)
            return
        # Newest first, keep a short recent list.
        for index, title in enumerate(reversed(titles[-20:]), start=1):
            absolute = len(titles) - index + 1
            ctk.CTkLabel(
                self.shot_list,
                text=f"{absolute:02d}. {title}",
                anchor="w",
            ).pack(fill="x", padx=4, pady=2)
