"""Molecule Lab panes — Atom / Molecule / Trial (left-rail leaves, not inner tabs)."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from idle_lab.feel_lab.themes import Look, default_look
from idle_lab.shell.paint import dormant_button_kwargs, paint_widget_tree, primary_button_kwargs


def build_molecule_atom_pane(
    parent,
    *,
    look: Look | None = None,
    on_open_atom_create: Callable[[], None] | None = None,
    on_goto_molecule: Callable[[], None] | None = None,
    on_goto_trial: Callable[[], None] | None = None,
    host_atom_pane=None,
):
    skin = look or default_look()
    root = ctk.CTkFrame(parent, fg_color=skin.bg)
    root.pack(fill="both", expand=True)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 4))
    ctk.CTkLabel(
        header,
        text="Molecule Lab · Atom",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=skin.line,
        anchor="w",
    ).pack(side="left")

    bar = ctk.CTkFrame(root, fg_color="transparent")
    bar.pack(fill="x", padx=12, pady=(0, 6))
    ctk.CTkButton(
        bar,
        text="Create Atom",
        width=120,
        command=(on_open_atom_create or (lambda: None)),
        state="normal" if on_open_atom_create else "disabled",
        **primary_button_kwargs(skin),
    ).pack(side="left")
    ctk.CTkButton(
        bar,
        text="Compose molecules →",
        width=160,
        command=(on_goto_molecule or (lambda: None)),
        state="normal" if on_goto_molecule else "disabled",
        **dormant_button_kwargs(skin),
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        bar,
        text="Trial →",
        width=80,
        command=(on_goto_trial or (lambda: None)),
        state="normal" if on_goto_trial else "disabled",
        **dormant_button_kwargs(skin),
    ).pack(side="left", padx=(8, 0))
    ctk.CTkLabel(
        bar,
        text="LOL actuations must show as atoms below — no silent gaps",
        text_color=skin.muted,
    ).pack(side="left", padx=(12, 0))

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_atom_pane is not None:
        host_atom_pane(host)
    else:
        ctk.CTkLabel(
            host,
            text="Atom library mounts when App wires this pane.",
            text_color=skin.muted,
        ).pack(anchor="w", pady=12)
    return root


def build_molecule_compose_pane(
    parent,
    *,
    look: Look | None = None,
    on_open_composer: Callable[[], None] | None = None,
    on_goto_trial: Callable[[], None] | None = None,
    host_composer=None,
):
    skin = look or default_look()
    root = ctk.CTkFrame(parent, fg_color=skin.bg)
    root.pack(fill="both", expand=True)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 4))
    ctk.CTkLabel(
        header,
        text="Molecule Lab · Molecule",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=skin.line,
        anchor="w",
    ).pack(side="left")

    toolbar = ctk.CTkFrame(root, fg_color="transparent")
    toolbar.pack(fill="x", padx=12, pady=(0, 6))
    ctk.CTkButton(
        toolbar,
        text="Pop out composer",
        width=140,
        command=(on_open_composer or (lambda: None)),
        state="normal" if on_open_composer else "disabled",
        **primary_button_kwargs(skin),
    ).pack(side="left")
    ctk.CTkButton(
        toolbar,
        text="Trial →",
        width=80,
        command=(on_goto_trial or (lambda: None)),
        state="normal" if on_goto_trial else "disabled",
        **dormant_button_kwargs(skin),
    ).pack(side="left", padx=(8, 0))
    ctk.CTkLabel(
        toolbar,
        text="Compose here · Trial runs packs · Pop out for a floating Lab",
        text_color=skin.muted,
    ).pack(side="left", padx=(12, 0))

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_composer is not None:
        host_composer(host)
    else:
        ctk.CTkLabel(
            host,
            text="Composer mounts when App wires this pane.",
            text_color=skin.muted,
        ).pack(anchor="w", pady=12)
    return root


def build_molecule_trial_pane(parent, *, look: Look | None = None, host_automations=None):
    skin = look or default_look()
    root = ctk.CTkFrame(parent, fg_color=skin.bg)
    root.pack(fill="both", expand=True)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 4))
    ctk.CTkLabel(
        header,
        text="Molecule Lab · Trial",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=skin.line,
        anchor="w",
    ).pack(side="left")
    ctk.CTkLabel(
        header,
        text="Run selected atoms / molecules · Dry-run · Walkthrough",
        text_color=skin.muted,
        anchor="e",
    ).pack(side="right")

    host = ctk.CTkFrame(root, fg_color="transparent")
    host.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    if host_automations is not None:
        host_automations(host)
    else:
        ctk.CTkLabel(
            host,
            text="Trial panel mounts when App wires this pane.",
            text_color=skin.muted,
        ).pack(anchor="w", pady=12)
    return root


class AtomLabPane(ctk.CTkFrame):
    """Atom library + LOL coverage board."""

    def __init__(
        self,
        master,
        *,
        look: Look | None = None,
        get_library_rows: Callable[[], list[dict[str, Any]]],
        get_coverage_rows: Callable[[], list[Any]],
        on_refresh: Callable[[], None],
        on_seed_missing: Callable[[], None],
        on_run_atom: Callable[[str], None],
        on_create_stub: Callable[[str], None] | None = None,
    ) -> None:
        self._look = look or default_look()
        super().__init__(master, fg_color="transparent")
        self.get_library_rows = get_library_rows
        self.get_coverage_rows = get_coverage_rows
        self.on_refresh = on_refresh
        self.on_seed_missing = on_seed_missing
        self.on_run_atom = on_run_atom
        self.on_create_stub = on_create_stub
        self._selected_id: str | None = None
        self._build()
        self.refresh()

    def apply_look(self, look: Look) -> None:
        self._look = look
        paint_widget_tree(self, look)

    def _build(self) -> None:
        skin = self._look
        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(
            tools,
            text="Refresh",
            width=90,
            command=self._refresh_clicked,
            **primary_button_kwargs(skin),
        ).pack(side="left")
        ctk.CTkButton(
            tools,
            text="Seed missing LOL wrappers",
            width=180,
            command=self._seed_clicked,
            **dormant_button_kwargs(skin),
        ).pack(side="left", padx=(8, 0))
        self.run_btn = ctk.CTkButton(
            tools,
            text="Run selected once",
            width=140,
            command=self._run_clicked,
            state="disabled",
            **primary_button_kwargs(skin),
        )
        self.run_btn.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1, uniform="ml")
        body.grid_columnconfigure(1, weight=1, uniform="ml")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, **{"fg_color": skin.panel, "border_width": 1 if skin.style == "type" else 0, "border_color": skin.desc_border})
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(
            left,
            text="Atom library",
            font=ctk.CTkFont(weight="bold"),
            text_color=skin.line,
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(8, 2))
        self.lib_list = ctk.CTkScrollableFrame(left, height=360, fg_color=skin.board)
        self.lib_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        right = ctk.CTkFrame(
            body,
            fg_color=skin.panel,
            border_width=1 if skin.style == "type" else 0,
            border_color=skin.desc_border,
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(
            right,
            text="LOL coverage",
            font=ctk.CTkFont(weight="bold"),
            text_color=skin.line,
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(
            right,
            text="Green = atom exists · Amber = seed · Gray = LOL-only chrome",
            text_color=skin.muted,
            anchor="w",
        ).pack(anchor="w", padx=8)
        self.cov_list = ctk.CTkScrollableFrame(right, height=360, fg_color=skin.board)
        self.cov_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _refresh_clicked(self) -> None:
        self.on_refresh()
        self.refresh()

    def _seed_clicked(self) -> None:
        self.on_seed_missing()
        self.refresh()

    def _run_clicked(self) -> None:
        if self._selected_id:
            self.on_run_atom(self._selected_id)

    def refresh(self) -> None:
        for child in self.lib_list.winfo_children():
            child.destroy()
        for child in self.cov_list.winfo_children():
            child.destroy()
        for row in self.get_library_rows():
            self._pack_library_row(row)
        for row in self.get_coverage_rows():
            self._pack_coverage_row(row)
        self.run_btn.configure(state="normal" if self._selected_id else "disabled")

    def _pack_library_row(self, row: dict[str, Any]) -> None:
        skin = self._look
        eid = str(row.get("id") or "")
        title = str(row.get("title") or eid)
        tags = ", ".join(row.get("tags") or ())
        ghost = "" if row.get("creator_ok") else " · JSON-only / needs creator"
        enabled = "on" if row.get("enabled") else "off"
        frame = ctk.CTkFrame(self.lib_list, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        selected = eid == self._selected_id
        btn = ctk.CTkButton(
            frame,
            text=f"{title}",
            anchor="w",
            fg_color=skin.live_bg if selected else "transparent",
            hover_color=skin.live_hover,
            text_color=skin.live_text if selected else skin.line,
            border_width=1 if skin.style == "type" and selected else 0,
            border_color=skin.live_border,
            command=lambda i=eid: self._select(i),
        )
        btn.pack(fill="x")
        ctk.CTkLabel(
            frame,
            text=f"{eid} · {enabled} · {tags}{ghost}",
            anchor="w",
            text_color=skin.muted,
            font=ctk.CTkFont(size=11),
        ).pack(fill="x", padx=6)

    def _pack_coverage_row(self, row: Any) -> None:
        status = getattr(row, "status", "")
        color = {
            "covered": "#7CF0B8",
            "missing": "#E7C36A",
            "lol_only": "#7E8796",
            "routine": "#7CF0B8",
        }.get(status, "#9AA4B2")
        frame = ctk.CTkFrame(self.cov_list, fg_color="transparent")
        frame.pack(fill="x", pady=3)
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(
            top,
            text=getattr(row, "actuation", ""),
            anchor="w",
            text_color=color,
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", fill="x", expand=True)
        if status == "missing" and self.on_create_stub is not None:
            aid = getattr(row, "actuation", "")
            if aid and " " not in aid and not aid.startswith("routine"):
                ctk.CTkButton(
                    top,
                    text="Create stub",
                    width=90,
                    fg_color="#2A3140",
                    hover_color="#3A4558",
                    command=lambda a=aid: self._stub(a),
                ).pack(side="right")
        ctk.CTkLabel(
            frame,
            text=getattr(row, "note", ""),
            anchor="w",
            text_color="#9AA4B2",
            font=ctk.CTkFont(size=11),
            wraplength=320,
            justify="left",
        ).pack(fill="x", padx=4)

    def _select(self, eid: str) -> None:
        self._selected_id = eid
        self.refresh()

    def _stub(self, actuation: str) -> None:
        if self.on_create_stub is not None:
            self.on_create_stub(actuation)
            self.refresh()
