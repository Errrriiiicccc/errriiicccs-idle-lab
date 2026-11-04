"""Automations tab: available list, details, queue, console."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.automations.schema import Collection, Event
from idle_lab.automations.store import AutomationStore

CONSOLE_COLORS = {
    "info": "#9AA4B2",
    "ok": "#8EE0C2",
    "warn": "#E7C36A",
    "error": "#F09595",
    "run": "#8EE0C2",
}


class AutomationsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        store: AutomationStore,
        on_reload: Callable[[], None],
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.store = store
        self.on_reload = on_reload
        self.on_start = on_start
        self.on_stop = on_stop
        self._mode = ctk.StringVar(value="Events")
        self._selected_event: Event | None = None
        self._selected_collection: Collection | None = None
        self._build()

    def _build(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(toolbar, text="Automations", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        self.reload_button = ctk.CTkButton(toolbar, text="Reload", width=90, command=self.on_reload)
        self.reload_button.pack(side="right", padx=(6, 0))
        self.stop_button = ctk.CTkButton(toolbar, text="Stop", width=80, command=self.on_stop)
        self.stop_button.pack(side="right", padx=(6, 0))
        self.start_button = ctk.CTkButton(toolbar, text="Start", width=80, command=self.on_start)
        self.start_button.pack(side="right")

        columns = ctk.CTkFrame(self, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=8, pady=4)
        columns.grid_columnconfigure(0, weight=1, uniform="cols")
        columns.grid_columnconfigure(1, weight=2, uniform="cols")
        columns.grid_columnconfigure(2, weight=1, uniform="cols")
        columns.grid_rowconfigure(0, weight=1)

        col1 = ctk.CTkFrame(columns)
        col1.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(col1, text="Available", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
        mode_row = ctk.CTkFrame(col1, fg_color="transparent")
        mode_row.pack(fill="x", padx=8, pady=4)
        ctk.CTkRadioButton(mode_row, text="Events", variable=self._mode, value="Events", command=self.refresh_list).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkRadioButton(
            mode_row, text="Collections", variable=self._mode, value="Collections", command=self.refresh_list
        ).pack(side="left")
        self.list_box = ctk.CTkScrollableFrame(col1, height=280)
        self.list_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        col2 = ctk.CTkFrame(columns)
        col2.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(col2, text="Details", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.details = ctk.CTkTextbox(col2, height=280, wrap="word", activate_scrollbars=True)
        self.details.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.details.configure(state="disabled")

        col3 = ctk.CTkFrame(columns)
        col3.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(col3, text="Queue", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.queue_box = ctk.CTkScrollableFrame(col3, height=280)
        self.queue_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        console_frame = ctk.CTkFrame(self)
        console_frame.pack(fill="both", expand=False, padx=8, pady=(4, 8))
        ctk.CTkLabel(console_frame, text="Console", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        self.console = ctk.CTkTextbox(console_frame, height=160, wrap="word")
        self.console.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.console.configure(state="disabled")

        self.refresh_list()
        self.set_queue([])

    def refresh_list(self) -> None:
        for child in self.list_box.winfo_children():
            child.destroy()
        if self._mode.get() == "Events":
            items = sorted(self.store.events.values(), key=lambda event: event.title.lower())
            if not items:
                ctk.CTkLabel(self.list_box, text="No events loaded.", text_color="#9AA4B2").pack(anchor="w", padx=4)
            for event in items:
                label = f"{event.title}  (p{event.priority})"
                btn = ctk.CTkButton(
                    self.list_box,
                    text=label,
                    anchor="w",
                    fg_color="transparent",
                    command=lambda e=event: self._select_event(e),
                )
                btn.pack(fill="x", pady=2)
        else:
            items = sorted(self.store.collections.values(), key=lambda collection: collection.title.lower())
            if not items:
                ctk.CTkLabel(self.list_box, text="No collections loaded.", text_color="#9AA4B2").pack(anchor="w", padx=4)
            for collection in items:
                btn = ctk.CTkButton(
                    self.list_box,
                    text=collection.title,
                    anchor="w",
                    fg_color="transparent",
                    command=lambda c=collection: self._select_collection(c),
                )
                btn.pack(fill="x", pady=2)

    def _select_event(self, event: Event) -> None:
        self._selected_event = event
        self._selected_collection = None
        lines = [
            f"Title: {event.title}",
            f"Id: {event.id}",
            f"Timing: every {event.every_ms} ms",
            f"Priority: {event.priority}",
            f"Enabled: {event.enabled}",
            "",
            "── Actions ──",
        ]
        for index, action in enumerate(event.actions, start=1):
            summary = action.type
            if action.type == "ocr":
                summary += f": {action.raw.get('roi')} → {action.raw.get('variable')}"
            elif action.type in {"mouse", "play_preset"}:
                summary += f": preset={action.raw.get('preset') or action.raw.get('name')}"
            elif action.type == "record_clip":
                summary += f": {action.raw.get('duration_s', 10)}s"
            elif action.type == "decide":
                summary += (
                    f": if {action.raw.get('variable')} {action.raw.get('mode')} "
                    f"{action.raw.get('match_a')!r} → A else B"
                )
            elif action.type == "log":
                summary += f": {action.raw.get('message')}"
            lines.append(f"{index}. {summary}")
            if action.type == "decide":
                if action.raw.get("explain_a"):
                    lines.append(f"   PATH A: {action.raw.get('explain_a')}")
                if action.raw.get("explain_b"):
                    lines.append(f"   PATH B: {action.raw.get('explain_b')}")
        if event.notes:
            lines.extend(["", f"Notes: {event.notes}"])
        self._set_details("\n".join(lines))

    def _select_collection(self, collection: Collection) -> None:
        self._selected_collection = collection
        self._selected_event = None
        lines = [
            f"Title: {collection.title}",
            f"Id: {collection.id}",
            f"Loop: {collection.loop}",
            f"Stop when: {collection.stop_when or '—'}",
            f"Branch variable: {collection.branch_variable}",
            "",
            "── Children (order) ──",
        ]
        for index, child_id in enumerate(collection.children, start=1):
            lines.append(f"{index}. {child_id}")
        if collection.branches:
            lines.extend(["", "── Branches ──"])
            for key, child_id in collection.branches.items():
                lines.append(f"{collection.branch_variable}={key} → {child_id}")
        if collection.notes:
            lines.extend(["", f"Notes: {collection.notes}"])
        self._set_details("\n".join(lines))

    def _set_details(self, text: str) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def set_queue(self, items: list[dict]) -> None:
        for child in self.queue_box.winfo_children():
            child.destroy()
        if not items:
            ctk.CTkLabel(self.queue_box, text="Idle.", text_color="#9AA4B2").pack(anchor="w", padx=4)
            return
        for item in items:
            status = item.get("status", "")
            marker = {"running": "▶", "deferred": "○", "waiting": "·", "done": "✔"}.get(status, "·")
            title = item.get("title") or item.get("event_id") or "?"
            detail = item.get("detail") or status
            color = "#8EE0C2" if status == "running" else ("#E7C36A" if status == "deferred" else "#C5D0DC")
            ctk.CTkLabel(
                self.queue_box,
                text=f"{marker} {title}\n   {detail}",
                anchor="w",
                justify="left",
                text_color=color,
            ).pack(fill="x", padx=4, pady=3)

    def append_console(self, message: str, level: str = "info") -> None:
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")
