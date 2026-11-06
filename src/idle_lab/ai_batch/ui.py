"""Missions workspace — AI Information Batch Gathering."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from idle_lab.ai_batch.schema import AiBatch, BatchRequest
from idle_lab.ai_batch.store import AiBatchStore
from idle_lab.comment_ui import make_comment_button
from idle_lab.comments import CommentStore, mission_comment_path, mission_request_comment_path
from idle_lab.scroll_memory import ScrollMemory


STATUS_COLOR = {
    "pending": "#9AA4B2",
    "running": "#8EE0C2",
    "completed": "#8EE0C2",
    "partial": "#E7C36A",
    "failed": "#F09595",
    "done": "#8EE0C2",
    "skipped": "#9AA4B2",
    "missed": "#F09595",
}


class AiBatchPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        store: AiBatchStore,
        scroll: ScrollMemory,
        screen_maps_root: Path,
        on_reload: Callable[[], None],
        on_new_batch: Callable[[], None],
        on_open_folder: Callable[[AiBatch], None],
        on_view_screenshots: Callable[[AiBatch], None],
        on_link_screen_map: Callable[[AiBatch], None],
        on_mark_request: Callable[[AiBatch, BatchRequest, str], None],
        on_add_feedback: Callable[[AiBatch], None],
        on_open_screen_map_batch: Callable[[str], None],
        on_snapshot_event: Callable[[AiBatch, BatchRequest], None] | None = None,
        on_start_run: Callable[[AiBatch], None] | None = None,
        on_stop_run: Callable[[], None] | None = None,
        on_export_packet: Callable[[], None] | None = None,
        on_comment_batch: Callable[[AiBatch], None] | None = None,
        on_comment_request: Callable[[AiBatch, BatchRequest], None] | None = None,
        comments: CommentStore | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.store = store
        self.scroll = scroll
        self.screen_maps_root = Path(screen_maps_root)
        self.on_reload = on_reload
        self.on_new_batch = on_new_batch
        self.on_open_folder = on_open_folder
        self.on_view_screenshots = on_view_screenshots
        self.on_link_screen_map = on_link_screen_map
        self.on_mark_request = on_mark_request
        self.on_add_feedback = on_add_feedback
        self.on_open_screen_map_batch = on_open_screen_map_batch
        self.on_snapshot_event = on_snapshot_event
        self.on_start_run = on_start_run
        self.on_stop_run = on_stop_run
        self.on_export_packet = on_export_packet
        self.on_comment_batch = on_comment_batch
        self.on_comment_request = on_comment_request
        self.comments = comments
        self._filter = ctk.StringVar(value="all")
        self._sort = ctk.StringVar(value="updated")
        self._selected: AiBatch | None = None
        self._running = False
        self._build()

    def _build(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(
            toolbar,
            text="Missions",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left")
        self.reload_button = ctk.CTkButton(toolbar, text="Reload", width=90, command=self.on_reload)
        self.reload_button.pack(side="right", padx=(6, 0))
        self.new_button = ctk.CTkButton(toolbar, text="New mission…", width=120, command=self.on_new_batch)
        self.new_button.pack(side="right", padx=(6, 0))
        self.packet_button = ctk.CTkButton(
            toolbar,
            text="Export packet",
            width=110,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._export_packet,
        )
        self.packet_button.pack(side="right", padx=(6, 0))
        self.stop_button = ctk.CTkButton(
            toolbar,
            text="Stop",
            width=80,
            fg_color="#5A3030",
            hover_color="#7A4040",
            command=self._stop_run,
            state="disabled",
        )
        self.stop_button.pack(side="right", padx=(6, 0))
        self.start_button = ctk.CTkButton(toolbar, text="Start", width=90, command=self._start_run)
        self.start_button.pack(side="right")

        help_frame = ctk.CTkFrame(self)
        help_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(
            help_frame,
            text=(
                "Select a mission → Start. Offline missions (OCR fixture bench) need no Anchor; live ones do. "
                "Failed steps screenshot into the linked Observe batch. After chat edits files, hit global Refresh (F5) — "
                "not Restart. Use comment bubbles for mid-run notes."
            ),
            anchor="w",
            justify="left",
            wraplength=980,
            text_color="#9AA4B2",
        ).pack(fill="x", padx=10, pady=8)
        self.run_status = ctk.CTkLabel(help_frame, text="Runner: idle", anchor="w", text_color="#8EE0C2")
        self.run_status.pack(fill="x", padx=10, pady=(0, 8))

        columns = ctk.CTkFrame(self, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=8, pady=4)
        columns.grid_columnconfigure(0, weight=1, uniform="ai")
        columns.grid_columnconfigure(1, weight=2, uniform="ai")
        columns.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(columns)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(left, text="Missions", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        filters = ctk.CTkFrame(left, fg_color="transparent")
        filters.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(filters, text="Filter", text_color="#9AA4B2").pack(side="left")
        self.filter_menu = ctk.CTkOptionMenu(
            filters,
            variable=self._filter,
            values=["all", "open", "completed", "pending", "running", "partial", "failed"],
            width=110,
            command=lambda _v: self.refresh_list(),
        )
        self.filter_menu.pack(side="left", padx=(6, 10))
        ctk.CTkLabel(filters, text="Sort", text_color="#9AA4B2").pack(side="left")
        self.sort_menu = ctk.CTkOptionMenu(
            filters,
            variable=self._sort,
            values=["updated", "created", "name", "status"],
            width=110,
            command=lambda _v: self.refresh_list(),
        )
        self.sort_menu.pack(side="left", padx=(6, 0))

        self.list_box = ctk.CTkScrollableFrame(left, height=360)
        self.list_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.scroll.register("ai.batches", self.list_box)

        right = ctk.CTkFrame(columns)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        header = ctk.CTkFrame(right, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(header, text="Mission detail", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.open_observe_btn = ctk.CTkButton(
            header,
            text="Open linked Observe",
            width=150,
            command=self._open_linked_observe,
            state="disabled",
        )
        self.open_observe_btn.pack(side="right", padx=(6, 0))
        self.view_shots_btn = ctk.CTkButton(
            header, text="View screenshots", width=130, command=self._view_shots, state="disabled"
        )
        self.view_shots_btn.pack(side="right", padx=(6, 0))
        self.open_folder_btn = ctk.CTkButton(
            header, text="Open folder", width=100, command=self._open_folder, state="disabled"
        )
        self.open_folder_btn.pack(side="right", padx=(6, 0))
        self.link_map_btn = ctk.CTkButton(
            header, text="Link Observe…", width=120, command=self._link_map, state="disabled"
        )
        self.link_map_btn.pack(side="right")

        self.summary = ctk.CTkLabel(right, text="Select a mission.", anchor="w", justify="left", wraplength=560)
        self.summary.pack(fill="x", padx=10, pady=(2, 4))

        self.detail_box = ctk.CTkScrollableFrame(right, height=280)
        self.detail_box.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.scroll.register("ai.detail", self.detail_box)

        feedback_bar = ctk.CTkFrame(right, fg_color="transparent")
        feedback_bar.pack(fill="x", padx=8, pady=(0, 8))
        self.feedback_btn = ctk.CTkButton(
            feedback_bar,
            text="Add feedback (missed something)…",
            command=self._add_feedback,
            state="disabled",
            fg_color="#2A3140",
            hover_color="#3A4558",
        )
        self.feedback_btn.pack(side="left")

        self.refresh_list()

    def refresh_list(self) -> None:
        def rebuild() -> None:
            for child in self.list_box.winfo_children():
                child.destroy()
            items = self.store.list_batches(status_filter=self._filter.get(), sort_key=self._sort.get())
            if not items:
                ctk.CTkLabel(self.list_box, text="No batches yet.", text_color="#9AA4B2").pack(anchor="w", padx=4)
                return
            selected_slug = self._selected.slug if self._selected else None
            for batch in items:
                already = " · already ran" if batch.status == "completed" else ""
                genre_tag = f"[{batch.genre}] " if batch.genre else ""
                runnable = sum(1 for req in batch.requests if req.runnable)
                color = STATUS_COLOR.get(batch.status, "#C5D0DC")
                row = ctk.CTkFrame(self.list_box, fg_color="transparent")
                row.pack(fill="x", pady=3)
                top = ctk.CTkFrame(row, fg_color="transparent")
                top.pack(fill="x")
                btn = ctk.CTkButton(
                    top,
                    text=f"{genre_tag}{batch.name}  · {batch.status}{already}",
                    anchor="w",
                    fg_color="#1F2A3A" if batch.slug == selected_slug else "transparent",
                    text_color=color,
                    command=lambda b=batch: self._select(b),
                )
                btn.pack(side="left", fill="x", expand=True)
                if self.on_comment_batch is not None:
                    path = mission_comment_path(batch.slug)
                    has = bool(self.comments and self.comments.has(path))
                    make_comment_button(
                        top,
                        has_notes=has,
                        command=lambda b=batch: self.on_comment_batch(b),
                    ).pack(side="right", padx=(4, 0))
                ctk.CTkLabel(
                    row,
                    text=(
                        f"{batch.done_count}/{batch.request_count} requests  ·  "
                        f"{runnable} runnable  ·  {batch.slug}"
                    ),
                    anchor="w",
                    text_color="#9AA4B2",
                    font=ctk.CTkFont(size=11),
                ).pack(fill="x", padx=8)

        self.scroll.around_rebuild("ai.batches", rebuild)
        if self._selected and self._selected.slug in self.store.batches:
            self._selected = self.store.batches[self._selected.slug]
            self._render_detail()
        elif self._selected:
            self._selected = None
            self._render_detail()

    def _select(self, batch: AiBatch) -> None:
        self._selected = batch
        self.refresh_list()

    def _render_detail(self) -> None:
        def rebuild() -> None:
            for child in self.detail_box.winfo_children():
                child.destroy()
            batch = self._selected
            enabled = batch is not None
            state = "normal" if enabled else "disabled"
            self.view_shots_btn.configure(state=state)
            self.open_folder_btn.configure(state=state)
            self.link_map_btn.configure(state=state)
            self.feedback_btn.configure(state=state)
            has_link = bool(batch and batch.linked_screen_map_batches)
            self.open_observe_btn.configure(state="normal" if has_link else "disabled")
            if batch is None:
                self.summary.configure(text="Select a mission.")
                ctk.CTkLabel(self.detail_box, text="Nothing selected.", text_color="#9AA4B2").pack(anchor="w")
                return

            already = "Yes — treat as already ran." if batch.status == "completed" else "No"
            runnable = sum(1 for req in batch.requests if req.runnable)
            genre_line = f"Genre: {batch.genre}  ·  " if batch.genre else ""
            self.summary.configure(
                text=(
                    f"{batch.name}\n"
                    f"Status: {batch.status}  ·  Already ran: {already}  ·  Runnable requests: {runnable}\n"
                    f"{genre_line}By: {batch.created_by}  ·  Updated: {batch.updated_at or '—'}\n"
                    f"Goal: {batch.goal or '(none)'}"
                )
            )

            ctk.CTkLabel(
                self.detail_box,
                text="Requests / what was taken",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(anchor="w", padx=4, pady=(4, 6))

            if not batch.requests:
                ctk.CTkLabel(
                    self.detail_box,
                    text="No requests listed. Edit batch.json or create a richer AI spec.",
                    text_color="#9AA4B2",
                ).pack(anchor="w", padx=4)

            for req in batch.requests:
                self._render_request(req, batch)

            if batch.linked_screen_map_batches:
                ctk.CTkLabel(
                    self.detail_box,
                    text="Linked Observe batches",
                    font=ctk.CTkFont(size=13, weight="bold"),
                ).pack(anchor="w", padx=4, pady=(12, 4))
                for slug in batch.linked_screen_map_batches:
                    ctk.CTkButton(
                        self.detail_box,
                        text=f"Open Observe: {slug}",
                        anchor="w",
                        command=lambda s=slug: self.on_open_screen_map_batch(s),
                    ).pack(fill="x", padx=4, pady=2)

            if batch.feedback:
                ctk.CTkLabel(
                    self.detail_box,
                    text="Feedback / gaps for the AI",
                    font=ctk.CTkFont(size=13, weight="bold"),
                ).pack(anchor="w", padx=4, pady=(12, 4))
                for note in batch.feedback:
                    ctk.CTkLabel(
                        self.detail_box,
                        text=f"[{note.author} · {note.at}]\n{note.text}",
                        anchor="w",
                        justify="left",
                        wraplength=520,
                        text_color="#E7C36A",
                    ).pack(fill="x", padx=4, pady=3)

        self.scroll.around_rebuild("ai.detail", rebuild)

    def _render_request(self, req: BatchRequest, batch: AiBatch) -> None:
        color = STATUS_COLOR.get(req.status, "#C5D0DC")
        box = ctk.CTkFrame(self.detail_box)
        box.pack(fill="x", padx=4, pady=4)
        step_n = len(req.steps)
        step_hint = f"  ·  {step_n} step(s)" if step_n else "  ·  no steps (manual/skip)"
        ctk.CTkLabel(
            box,
            text=f"{req.status.upper()}  ·  {req.kind}  ·  {req.label}{step_hint}",
            anchor="w",
            text_color=color,
            font=ctk.CTkFont(weight="bold"),
        ).pack(fill="x", padx=8, pady=(6, 2))
        if req.detail:
            ctk.CTkLabel(
                box,
                text=req.detail,
                anchor="w",
                justify="left",
                wraplength=500,
                text_color="#9AA4B2",
            ).pack(fill="x", padx=8)
        if req.result is not None:
            bits = []
            if req.result.summary:
                bits.append(req.result.summary)
            if req.result.path:
                bits.append(f"path: {req.result.path}")
            if req.result.screen_map_batch:
                shot = req.result.screen_map_shot or "(batch)"
                bits.append(f"screen-map: {req.result.screen_map_batch} / {shot}")
            if req.result.event_id:
                bits.append(f"event: {req.result.event_id}")
            if req.result.captured_at:
                bits.append(f"at: {req.result.captured_at}")
            if bits:
                ctk.CTkLabel(
                    box,
                    text="Taken → " + " · ".join(bits),
                    anchor="w",
                    justify="left",
                    wraplength=500,
                    text_color="#8EE0C2",
                ).pack(fill="x", padx=8, pady=(2, 0))
        elif req.status == "pending":
            ctk.CTkLabel(box, text="Taken → (nothing yet)", anchor="w", text_color="#9AA4B2").pack(
                fill="x", padx=8, pady=(2, 0)
            )

        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkButton(
            actions,
            text="Mark done",
            width=90,
            command=lambda r=req, b=batch: self.on_mark_request(b, r, "done"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            actions,
            text="Missed",
            width=80,
            fg_color="#5A3030",
            hover_color="#7A4040",
            command=lambda r=req, b=batch: self.on_mark_request(b, r, "missed"),
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            actions,
            text="Skip",
            width=70,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=lambda r=req, b=batch: self.on_mark_request(b, r, "skipped"),
        ).pack(side="left", padx=(0, 4))
        if req.kind == "event_snapshot" and self.on_snapshot_event is not None:
            ctk.CTkButton(
                actions,
                text="Snapshot event",
                width=120,
                fg_color="#2A3140",
                hover_color="#3A4558",
                command=lambda r=req, b=batch: self.on_snapshot_event(b, r),
            ).pack(side="left", padx=(0, 4))
        if self.on_comment_request is not None:
            path = mission_request_comment_path(batch.slug, req.id)
            has = bool(self.comments and self.comments.has(path))
            make_comment_button(
                actions,
                has_notes=has,
                command=lambda r=req, b=batch: self.on_comment_request(b, r),
            ).pack(side="right")

    def _open_linked_observe(self) -> None:
        if self._selected is None or not self._selected.linked_screen_map_batches:
            return
        self.on_open_screen_map_batch(self._selected.linked_screen_map_batches[-1])

    def _view_shots(self) -> None:
        if self._selected is not None:
            self.on_view_screenshots(self._selected)

    def _open_folder(self) -> None:
        if self._selected is not None:
            self.on_open_folder(self._selected)

    def _link_map(self) -> None:
        if self._selected is not None:
            self.on_link_screen_map(self._selected)

    def _add_feedback(self) -> None:
        if self._selected is not None:
            self.on_add_feedback(self._selected)

    def _export_packet(self) -> None:
        if self.on_export_packet is not None:
            self.on_export_packet()

    def _start_run(self) -> None:
        if self.on_start_run is None:
            return
        if self._selected is None:
            self.run_status.configure(text="Runner: select a batch first.", text_color="#E7C36A")
            return
        self.on_start_run(self._selected)

    def _stop_run(self) -> None:
        if self.on_stop_run is not None:
            self.on_stop_run()

    def set_running(self, running: bool, message: str | None = None) -> None:
        self._running = running
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        if message:
            self.run_status.configure(
                text=message,
                text_color="#8EE0C2" if running else "#9AA4B2",
            )
        elif running:
            self.run_status.configure(text="Runner: running…", text_color="#8EE0C2")
        else:
            self.run_status.configure(text="Runner: idle", text_color="#9AA4B2")

    def set_run_message(self, message: str, *, level: str = "info") -> None:
        color = {
            "ok": "#8EE0C2",
            "run": "#8EE0C2",
            "warn": "#E7C36A",
            "error": "#F09595",
            "info": "#9AA4B2",
        }.get(level, "#9AA4B2")
        self.run_status.configure(text=message, text_color=color)
