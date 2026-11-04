"""Screen Map tab UI — capture mode + batch browser + screenshot viewer hooks."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from idle_lab.screen_map.catalog import BatchSummary
from idle_lab.scroll_memory import ScrollMemory


class ScreenMapPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        on_start_batch: Callable[[], None],
        on_end_batch: Callable[[], None],
        on_open_folder: Callable[[], None],
        on_refresh_catalog: Callable[[], None],
        on_view_shot: Callable[[BatchSummary, int], None],
        on_view_batch: Callable[[BatchSummary], None],
        scroll: ScrollMemory | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_start_batch = on_start_batch
        self.on_end_batch = on_end_batch
        self.on_open_folder = on_open_folder
        self.on_refresh_catalog = on_refresh_catalog
        self.on_view_shot = on_view_shot
        self.on_view_batch = on_view_batch
        self.scroll = scroll or ScrollMemory()
        self._busy_message: str | None = None
        self._catalog: list[BatchSummary] = []
        self._selected: BatchSummary | None = None
        self._focus_slug: str | None = None
        self._build()

    @property
    def selected_batch(self) -> BatchSummary | None:
        return self._selected

    def _build(self) -> None:
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

        toolbar = ctk.CTkFrame(self._content, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(toolbar, text="Screen Map", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.refresh_button = ctk.CTkButton(
            toolbar, text="Refresh", width=90, command=self.on_refresh_catalog, fg_color="#2A3140", hover_color="#3A4558"
        )
        self.refresh_button.pack(side="right", padx=(6, 0))
        self.open_button = ctk.CTkButton(toolbar, text="Open folder", width=110, command=self.on_open_folder)
        self.open_button.pack(side="right", padx=(6, 0))
        self.end_button = ctk.CTkButton(toolbar, text="End batch", width=100, command=self.on_end_batch)
        self.end_button.pack(side="right", padx=(6, 0))
        self.start_button = ctk.CTkButton(toolbar, text="Start batch…", width=120, command=self.on_start_batch)
        self.start_button.pack(side="right")

        status = ctk.CTkFrame(self._content)
        status.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(status, text="Capture status", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 2)
        )
        self.mode_label = ctk.CTkLabel(status, text="Screenshot mode: OFF", anchor="w")
        self.mode_label.pack(fill="x", padx=10)
        self.path_label = ctk.CTkLabel(status, text="Active batch: (none)", anchor="w", wraplength=900)
        self.path_label.pack(fill="x", padx=10, pady=(2, 0))
        self.count_label = ctk.CTkLabel(status, text="Shots this session: 0", anchor="w")
        self.count_label.pack(fill="x", padx=10, pady=(2, 0))
        self.hint_label = ctk.CTkLabel(status, text="", anchor="w", text_color="#9AA4B2")
        self.hint_label.pack(fill="x", padx=10, pady=(2, 10))

        help_frame = ctk.CTkFrame(self._content)
        help_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(
            help_frame,
            text=(
                "Anchor the emulator first (top ANCHOR bar). Start a batch, then press Space: Idle Lab "
                "captures immediately, then asks for a title. Esc cancels an open title dialog; Esc again "
                "ends the batch. Browse past batches below — click a shot to view the screenshot. "
                "Scroll position stays until you leave and come back or restart the app. "
                "Middle-drag (or drag empty areas) to scrub long lists."
            ),
            anchor="w",
            justify="left",
            wraplength=900,
            text_color="#9AA4B2",
        ).pack(fill="x", padx=10, pady=10)

        columns = ctk.CTkFrame(self._content, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        columns.grid_columnconfigure(0, weight=1, uniform="sm")
        columns.grid_columnconfigure(1, weight=2, uniform="sm")
        columns.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(columns)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(left, text="Screenshot batches", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        self.batch_list = ctk.CTkScrollableFrame(left, height=320)
        self.batch_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.scroll.register("screen_map.batches", self.batch_list)

        right = ctk.CTkFrame(columns)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        header = ctk.CTkFrame(right, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(header, text="Screens in batch", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.view_all_btn = ctk.CTkButton(
            header, text="View all screenshots", width=150, command=self._view_all, state="disabled"
        )
        self.view_all_btn.pack(side="right")
        self.shots_caption = ctk.CTkLabel(right, text="Select a batch.", anchor="w", text_color="#9AA4B2")
        self.shots_caption.pack(fill="x", padx=10, pady=(0, 4))
        self.shot_list = ctk.CTkScrollableFrame(right, height=320)
        self.shot_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.scroll.register("screen_map.shots", self.shot_list)

        self._busy_overlay = ctk.CTkFrame(self, fg_color=("#1a1a1a", "#1a1a1a"))
        self._busy_card = ctk.CTkFrame(self._busy_overlay, fg_color=("#2b2b2b", "#2b2b2b"))
        self._busy_card.place(relx=0.5, rely=0.5, anchor="center")
        self._busy_title = ctk.CTkLabel(
            self._busy_card,
            text="Working…",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self._busy_title.pack(padx=36, pady=(28, 8))
        self._busy_detail = ctk.CTkLabel(
            self._busy_card,
            text="Please wait — Space is paused.",
            text_color="#9AA4B2",
        )
        self._busy_detail.pack(padx=36, pady=(0, 28))

        self.set_idle()
        self.set_catalog([])

    def set_idle(self) -> None:
        self._busy_message = None
        self._hide_busy()
        self.mode_label.configure(text="Screenshot mode: OFF")
        self.path_label.configure(text="Active batch: (none)")
        self.count_label.configure(text="Shots this session: 0")
        self.hint_label.configure(text="")
        self.start_button.configure(state="normal")
        self.end_button.configure(state="disabled")
        self.open_button.configure(state="normal")

    def set_active(self, folder: Path, titles: list[str], *, ready: bool = True) -> None:
        self.mode_label.configure(text="Screenshot mode: ON")
        self.path_label.configure(text=f"Active batch: {folder}")
        self.count_label.configure(text=f"Shots this session: {len(titles)}")
        self.hint_label.configure(
            text="Ready — press Space to capture." if ready else "Busy — wait for the loading screen to finish."
        )
        self.start_button.configure(state="disabled")
        self.end_button.configure(state="normal")
        self.open_button.configure(state="normal")

    def set_busy(self, message: str | None) -> None:
        """Show or hide the full-tab loading overlay. ``None`` clears it."""

        self._busy_message = message
        if not message:
            self._hide_busy()
            return
        self._busy_title.configure(text=message)
        self._busy_detail.configure(text="Please wait — Space is paused until this finishes.")
        self._busy_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._busy_overlay.lift()
        self.update_idletasks()

    def _hide_busy(self) -> None:
        self._busy_overlay.place_forget()

    def set_catalog(self, batches: list[BatchSummary], *, focus_slug: str | None = None) -> None:
        self._catalog = list(batches)
        if focus_slug:
            self._focus_slug = focus_slug
        if self._focus_slug:
            match = next((b for b in self._catalog if b.slug == self._focus_slug), None)
            self._selected = match
        elif self._selected is not None:
            match = next((b for b in self._catalog if b.slug == self._selected.slug), None)
            self._selected = match
        self._render_batches()
        self._render_shots()

    def focus_batch(self, slug: str) -> None:
        self._focus_slug = slug
        match = next((b for b in self._catalog if b.slug == slug), None)
        self._selected = match
        self._render_batches()
        self._render_shots()

    def _render_batches(self) -> None:
        def rebuild() -> None:
            for child in self.batch_list.winfo_children():
                child.destroy()
            if not self._catalog:
                ctk.CTkLabel(self.batch_list, text="No batches on disk yet.", text_color="#9AA4B2").pack(
                    anchor="w", padx=4
                )
                return
            selected_slug = self._selected.slug if self._selected else None
            for batch in self._catalog:
                row = ctk.CTkFrame(self.batch_list, fg_color="transparent")
                row.pack(fill="x", pady=3)
                btn = ctk.CTkButton(
                    row,
                    text=f"{batch.title}",
                    anchor="w",
                    fg_color="#1F2A3A" if batch.slug == selected_slug else "transparent",
                    command=lambda b=batch: self._select_batch(b),
                )
                btn.pack(fill="x")
                ctk.CTkLabel(
                    row,
                    text=f"{batch.shot_count} screen(s)  ·  {batch.slug}",
                    anchor="w",
                    text_color="#9AA4B2",
                    font=ctk.CTkFont(size=11),
                ).pack(fill="x", padx=8)

        self.scroll.around_rebuild("screen_map.batches", rebuild)

    def _select_batch(self, batch: BatchSummary) -> None:
        self._selected = batch
        self._focus_slug = batch.slug
        self._render_batches()
        self._render_shots()

    def _render_shots(self) -> None:
        def rebuild() -> None:
            for child in self.shot_list.winfo_children():
                child.destroy()
            batch = self._selected
            if batch is None:
                self.shots_caption.configure(text="Select a batch.")
                self.view_all_btn.configure(state="disabled")
                ctk.CTkLabel(self.shot_list, text="No batch selected.", text_color="#9AA4B2").pack(anchor="w", padx=4)
                return
            self.shots_caption.configure(
                text=f"{batch.title}  ·  {batch.shot_count} captured screen(s)  ·  {batch.folder}"
            )
            self.view_all_btn.configure(state="normal" if batch.shot_count else "disabled")
            if not batch.manifest.shots:
                ctk.CTkLabel(self.shot_list, text="This batch has no shots yet.", text_color="#9AA4B2").pack(
                    anchor="w", padx=4
                )
                return
            for index, shot in enumerate(batch.manifest.shots):
                row = ctk.CTkFrame(self.shot_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                exists = (batch.folder / shot.filename).exists()
                suffix = "" if exists else "  (missing file)"
                ctk.CTkButton(
                    row,
                    text=f"{shot.index:02d}. {shot.title}{suffix}",
                    anchor="w",
                    fg_color="transparent",
                    command=lambda b=batch, i=index: self.on_view_shot(b, i),
                ).pack(fill="x")
                meta = shot.captured_at or shot.filename
                ctk.CTkLabel(
                    row,
                    text=meta,
                    anchor="w",
                    text_color="#9AA4B2",
                    font=ctk.CTkFont(size=11),
                ).pack(fill="x", padx=8)

        self.scroll.around_rebuild("screen_map.shots", rebuild)

    def _view_all(self) -> None:
        if self._selected is not None:
            self.on_view_batch(self._selected)
