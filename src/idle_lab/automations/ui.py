"""Loops workspace: available list, details, queue, console."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.automations.describe import format_collection, format_event, list_caption
from idle_lab.automations.schema import Collection, Event
from idle_lab.automations.store import AutomationStore
from idle_lab.comment_ui import make_comment_button
from idle_lab.comments import CommentStore, collection_comment_path, event_comment_path
from idle_lab.scroll_memory import ScrollMemory
from idle_lab.taxonomy.browse import find_node, with_unfiled
from idle_lab.taxonomy.model import Taxonomy, TaxonomyNode


class AutomationsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        store: AutomationStore,
        on_reload: Callable[[], None],
        on_start: Callable[[Event | None, Collection | None], None],
        on_stop: Callable[[], None],
        on_start_all_enabled: Callable[[], None] | None = None,
        on_walkthrough: Callable[[Collection], None] | None = None,
        on_walkthrough_stop: Callable[[], None] | None = None,
        on_run_collection: Callable[[Collection], None] | None = None,
        on_validate: Callable[[], None] | None = None,
        on_dry_run: Callable[[Event | None, Collection | None], None] | None = None,
        on_comment_event: Callable[[str, str], None] | None = None,
        on_comment_collection: Callable[[str, str], None] | None = None,
        comments: CommentStore | None = None,
        scroll: ScrollMemory | None = None,
        taxonomy: Taxonomy | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.store = store
        self.taxonomy = taxonomy
        self.on_reload = on_reload
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_start_all_enabled = on_start_all_enabled
        self.on_walkthrough = on_walkthrough
        self.on_walkthrough_stop = on_walkthrough_stop
        self.on_run_collection = on_run_collection
        self.on_validate = on_validate
        self.on_dry_run = on_dry_run
        self.on_comment_event = on_comment_event
        self.on_comment_collection = on_comment_collection
        self.comments = comments
        self.scroll = scroll or ScrollMemory()
        self._mode = ctk.StringVar(value="Atoms")
        self._detail_mode = ctk.StringVar(value="Basic")
        self._selected_event: Event | None = None
        self._selected_collection: Collection | None = None
        self._browse_root: TaxonomyNode | None = None
        self._browse_stack: list[TaxonomyNode] = []
        self._build()

    def _build(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(toolbar, text="Loops", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        # CUT: Loops-local Reload — global Refresh only. Keep attribute for call sites.
        self.reload_button = ctk.CTkButton(toolbar, text="Reload", width=90, command=self.on_reload)
        self.stop_button = ctk.CTkButton(toolbar, text="Stop", width=80, command=self.on_stop)
        self.stop_button.pack(side="right", padx=(6, 0))
        self.start_button = ctk.CTkButton(toolbar, text="Start selected", width=110, command=self._start_selected)
        self.start_button.pack(side="right", padx=(0, 6))
        # CUT: Start all enabled — keep attribute for older call sites; do not pack.
        self.start_all_button = ctk.CTkButton(
            toolbar,
            text="Start all enabled",
            width=130,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._start_all_enabled,
        )
        self.run_pack_button = ctk.CTkButton(
            toolbar,
            text="Run pack",
            width=90,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._run_pack,
        )
        self.run_pack_button.pack(side="right", padx=(0, 6))
        self.dry_run_button = ctk.CTkButton(
            toolbar,
            text="Dry-run",
            width=80,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._dry_run,
        )
        self.dry_run_button.pack(side="right", padx=(0, 6))
        self.validate_button = ctk.CTkButton(
            toolbar,
            text="Validate",
            width=80,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._validate,
        )
        self.validate_button.pack(side="right", padx=(0, 6))
        self.walkthrough_button = ctk.CTkButton(
            toolbar,
            text="Walkthrough",
            width=110,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._start_walkthrough,
        )
        self.walkthrough_button.pack(side="right", padx=(0, 6))
        self.walkthrough_stop_button = ctk.CTkButton(
            toolbar,
            text="End tour",
            width=90,
            fg_color="#5A3030",
            hover_color="#7A4040",
            command=self._stop_walkthrough,
            state="disabled",
        )
        self.walkthrough_stop_button.pack(side="right", padx=(0, 6))

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
        ctk.CTkRadioButton(
            mode_row, text="Atoms", variable=self._mode, value="Atoms", command=self._on_mode_changed
        ).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(
            mode_row, text="Molecules", variable=self._mode, value="Molecules", command=self._on_mode_changed
        ).pack(side="left")
        nav_row = ctk.CTkFrame(col1, fg_color="transparent")
        nav_row.pack(fill="x", padx=8, pady=(0, 4))
        self.up_button = ctk.CTkButton(
            nav_row,
            text="Up",
            width=48,
            height=24,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._browse_up,
        )
        self.up_button.pack(side="left")
        self.crumb_label = ctk.CTkLabel(
            nav_row,
            text="",
            anchor="w",
            justify="left",
            text_color="#A8B4C4",
            font=ctk.CTkFont(size=11),
        )
        self.crumb_label.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.list_box = ctk.CTkScrollableFrame(col1, height=280)
        self.list_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.scroll.register("automations.list", self.list_box)

        col2 = ctk.CTkFrame(columns)
        col2.grid(row=0, column=1, sticky="nsew", padx=4)
        details_header = ctk.CTkFrame(col2, fg_color="transparent")
        details_header.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(details_header, text="Details", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        detail_toggle = ctk.CTkFrame(details_header, fg_color="transparent")
        detail_toggle.pack(side="right")
        ctk.CTkRadioButton(
            detail_toggle,
            text="Basic",
            variable=self._detail_mode,
            value="Basic",
            width=70,
            command=self._refresh_details,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkRadioButton(
            detail_toggle,
            text="Detailed",
            variable=self._detail_mode,
            value="Detailed",
            width=90,
            command=self._refresh_details,
        ).pack(side="left")
        self.details = ctk.CTkTextbox(col2, height=280, wrap="word", activate_scrollbars=True)
        self.details.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.details.configure(state="disabled")

        col3 = ctk.CTkFrame(columns)
        col3.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(col3, text="Queue", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=8, pady=(8, 2))
        self.queue_box = ctk.CTkScrollableFrame(col3, height=280)
        self.queue_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.scroll.register("automations.queue", self.queue_box)

        console_frame = ctk.CTkFrame(self)
        console_frame.pack(fill="both", expand=False, padx=8, pady=(4, 8))
        ctk.CTkLabel(console_frame, text="Console", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        self.console = ctk.CTkTextbox(console_frame, height=160, wrap="word")
        self.console.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.console.configure(state="disabled")

        self._reset_browse_root()
        self.refresh_list()
        self.set_queue([])

    def set_taxonomy(self, taxonomy: Taxonomy | None) -> None:
        self.taxonomy = taxonomy
        self._reset_browse_root()
        self.refresh_list()

    def _on_mode_changed(self) -> None:
        self._reset_browse_root()
        self.refresh_list()

    def _reset_browse_root(self) -> None:
        self._browse_stack = []
        self._browse_root = self._mode_root()

    def _mode_root(self) -> TaxonomyNode | None:
        if self.taxonomy is None:
            return None
        if self._mode.get() == "Atoms":
            node = find_node(self.taxonomy, "loops.events")
            if node is None:
                return None
            titles = {event.id: event.title for event in self.store.events.values()}
            return with_unfiled(
                node,
                kind="event",
                all_ids=self.store.events.keys(),
                titles=titles,
            )
        node = find_node(self.taxonomy, "loops.collections")
        if node is None:
            return None
        titles = {collection.id: collection.title for collection in self.store.collections.values()}
        return with_unfiled(
            node,
            kind="collection",
            all_ids=self.store.collections.keys(),
            titles=titles,
        )

    def _current_folder(self) -> TaxonomyNode | None:
        if self._browse_stack:
            return self._browse_stack[-1]
        return self._browse_root

    def _browse_up(self) -> None:
        if self._browse_stack:
            self._browse_stack.pop()
            self.refresh_list()

    def _enter_folder(self, node: TaxonomyNode) -> None:
        self._browse_stack.append(node)
        self.refresh_list()

    def refresh_list(self) -> None:
        def rebuild() -> None:
            for child in self.list_box.winfo_children():
                child.destroy()
            folder = self._current_folder()
            crumbs = []
            if self._browse_root is not None:
                crumbs.append(self._browse_root.label)
            crumbs.extend(node.label for node in self._browse_stack)
            self.crumb_label.configure(text=" › ".join(crumbs) if crumbs else "(no taxonomy)")
            self.up_button.configure(state="normal" if self._browse_stack else "disabled")

            if folder is None:
                ctk.CTkLabel(
                    self.list_box,
                    text="Taxonomy missing Atoms / Molecules roots (loops.events / loops.collections).",
                    text_color="#F09595",
                    wraplength=220,
                    justify="left",
                ).pack(anchor="w", padx=4)
                return
            if not folder.children:
                ctk.CTkLabel(self.list_box, text="Empty folder.", text_color="#9AA4B2").pack(anchor="w", padx=4)
                return
            for node in folder.children:
                if node.is_folder:
                    self._pack_folder_row(node)
                else:
                    self._pack_leaf_row(node)

        self.scroll.around_rebuild("automations.list", rebuild)

    def _pack_folder_row(self, node: TaxonomyNode) -> None:
        row = ctk.CTkFrame(self.list_box, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkButton(
            row,
            text=f"{node.label}  ›",
            anchor="w",
            fg_color="transparent",
            command=lambda n=node: self._enter_folder(n),
        ).pack(fill="x")
        if node.description:
            ctk.CTkLabel(
                row,
                text=node.description,
                anchor="w",
                justify="left",
                text_color="#9AA4B2",
                wraplength=220,
                font=ctk.CTkFont(size=11),
            ).pack(fill="x", padx=8)

    def _pack_leaf_row(self, node: TaxonomyNode) -> None:
        row = ctk.CTkFrame(self.list_box, fg_color="transparent")
        row.pack(fill="x", pady=3)
        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x")
        event, collection = self._leaf_targets(node)
        if event is not None:
            btn = ctk.CTkButton(
                top,
                text=f"{node.label}  · p{event.priority}",
                anchor="w",
                fg_color="transparent",
                command=lambda e=event: self._select_event(e),
            )
            btn.pack(side="left", fill="x", expand=True)
            if self.on_comment_event is not None:
                path = event_comment_path(event.id)
                has = bool(self.comments and self.comments.has(path))
                make_comment_button(
                    top,
                    has_notes=has,
                    command=lambda e=event: self.on_comment_event(e.id, e.title),
                ).pack(side="right", padx=(4, 0))
            caption = list_caption(event)
        elif collection is not None:
            branch_hint = f"  · {len(collection.branches)} branches" if collection.branches else ""
            btn = ctk.CTkButton(
                top,
                text=f"{node.label}{branch_hint}",
                anchor="w",
                fg_color="transparent",
                command=lambda c=collection: self._select_collection(c),
            )
            btn.pack(side="left", fill="x", expand=True)
            if self.on_comment_collection is not None:
                path = collection_comment_path(collection.id)
                has = bool(self.comments and self.comments.has(path))
                make_comment_button(
                    top,
                    has_notes=has,
                    command=lambda c=collection: self.on_comment_collection(c.id, c.title),
                ).pack(side="right", padx=(4, 0))
            caption = list_caption(collection)
        else:
            ctk.CTkButton(
                top,
                text=node.label,
                anchor="w",
                fg_color="transparent",
                command=lambda n=node: self._select_action_leaf(n),
            ).pack(side="left", fill="x", expand=True)
            caption = node.description or (node.action or {}).get("type", "action")
        ctk.CTkLabel(
            row,
            text=caption,
            anchor="w",
            justify="left",
            text_color="#9AA4B2",
            wraplength=220,
            font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=8)

    def _leaf_targets(self, node: TaxonomyNode) -> tuple[Event | None, Collection | None]:
        action = node.action or {}
        ref = node.ref or {}
        event_id = ""
        collection_id = ""
        if action.get("type") == "start_event":
            event_id = str(action.get("event") or "")
        elif action.get("type") == "start_collection":
            collection_id = str(action.get("collection") or "")
        elif ref.get("kind") == "event":
            event_id = str(ref.get("id") or "")
        elif ref.get("kind") == "collection":
            collection_id = str(ref.get("id") or "")
        event = self.store.events.get(event_id) if event_id else None
        collection = self.store.collections.get(collection_id) if collection_id else None
        return event, collection

    def _select_action_leaf(self, node: TaxonomyNode) -> None:
        self._selected_event = None
        self._selected_collection = None
        action = node.action or {}
        detail = node.description or ""
        lines = [
            node.label,
            "",
            detail,
            "",
            f"Action: {action.get('type', '?')}",
        ]
        for key, value in action.items():
            if key != "type":
                lines.append(f"  {key}: {value}")
        lines.append("")
        lines.append("Start selected only works for event/collection leaves.")
        if action.get("type") == "start_enabled_loops" and self.on_start_all_enabled is not None:
            lines.append("Use Start all enabled for this leaf.")
        self._set_details("\n".join(lines))

    def _select_event(self, event: Event) -> None:
        self._selected_event = event
        self._selected_collection = None
        self._refresh_details()

    def _select_collection(self, collection: Collection) -> None:
        self._selected_collection = collection
        self._selected_event = None
        self._refresh_details()

    def _start_walkthrough(self) -> None:
        if self.on_walkthrough is None:
            return
        if self._selected_collection is None:
            self.append_console("Select a Collection first, then click Walkthrough.", "warn")
            return
        self.on_walkthrough(self._selected_collection)

    def _start_selected(self) -> None:
        self.on_start(self._selected_event, self._selected_collection)

    def _start_all_enabled(self) -> None:
        if self.on_start_all_enabled is not None:
            self.on_start_all_enabled()
        else:
            self.append_console("Start all enabled is not wired.", "warn")

    def _run_pack(self) -> None:
        if self.on_run_collection is None:
            return
        if self._selected_collection is None:
            self.append_console("Select a Collection first, then click Run pack.", "warn")
            return
        self.on_run_collection(self._selected_collection)

    def _validate(self) -> None:
        if self.on_validate is not None:
            self.on_validate()

    def _dry_run(self) -> None:
        if self.on_dry_run is None:
            return
        self.on_dry_run(self._selected_event, self._selected_collection)

    def _stop_walkthrough(self) -> None:
        if self.on_walkthrough_stop is not None:
            self.on_walkthrough_stop()

    def set_walkthrough_active(self, active: bool) -> None:
        self.walkthrough_button.configure(state="disabled" if active else "normal")
        self.walkthrough_stop_button.configure(state="normal" if active else "disabled")

    def _refresh_details(self) -> None:
        detailed = self._detail_mode.get() == "Detailed"
        if self._selected_event is not None:
            text = format_event(self._selected_event, detailed=detailed, store=self.store)
        elif self._selected_collection is not None:
            text = format_collection(self._selected_collection, detailed=detailed, store=self.store)
        else:
            text = "Select an event or collection.\n\nBasic = plain-language summary.\nDetailed = exact paths, outputs, and branch rules."
        self._set_details(text)

    def _set_details(self, text: str) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def set_queue(self, items: list[dict]) -> None:
        def rebuild() -> None:
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

        self.scroll.around_rebuild("automations.queue", rebuild)

    def append_console(self, message: str, level: str = "info") -> None:
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")
