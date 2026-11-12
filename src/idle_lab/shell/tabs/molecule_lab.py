"""Molecule Lab tab — Atom library, Molecule composer, Trial browse/run."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk


def find_ml_root(widget) -> Any | None:
    """Walk ancestors for the Molecule Lab root that owns `_ml_tabs`."""

    cur = widget
    for _ in range(16):
        if cur is None:
            return None
        if getattr(cur, "_ml_tabs", None) is not None:
            return cur
        cur = getattr(cur, "master", None)
    return None


def select_ml_subtab(root_or_descendant, name: str) -> bool:
    """Switch Atom / Molecule / Trial. Accepts ML root or any descendant."""

    root = root_or_descendant
    tabs = getattr(root, "_ml_tabs", None)
    if tabs is None:
        root = find_ml_root(root_or_descendant)
        tabs = getattr(root, "_ml_tabs", None) if root is not None else None
    if tabs is None:
        return False
    try:
        tabs.set(str(name))
        return True
    except Exception:
        return False


def select_molecule_subtab(root) -> None:
    select_ml_subtab(root, "Molecule")


def select_atom_subtab(root) -> None:
    select_ml_subtab(root, "Atom")


def select_trial_subtab(root) -> None:
    select_ml_subtab(root, "Trial")


def build_molecule_lab_tab(
    parent,
    *,
    on_open_atom_create: Callable[[], None] | None = None,
    on_open_composer: Callable[[], None] | None = None,
    host_automations=None,
    host_composer=None,
    host_atom_pane=None,
    on_goto_molecule_tab: Callable[[], None] | None = None,
    on_goto_trial_tab: Callable[[], None] | None = None,
    on_register_root: Callable[[Any], None] | None = None,
):
    """host_* callbacks: App packs live panes into the given parent frames."""

    root = ctk.CTkFrame(parent, fg_color="transparent")
    root.pack(fill="both", expand=True)
    if on_register_root is not None:
        try:
            on_register_root(root)
        except Exception:
            pass

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(12, 4))
    ctk.CTkLabel(
        header,
        text="Molecule Lab",
        font=ctk.CTkFont(size=22, weight="bold"),
        anchor="w",
    ).pack(side="left")
    ctk.CTkLabel(
        header,
        text="Atom · Compose · Trial",
        text_color="#7E8796",
        anchor="e",
    ).pack(side="right")

    tabs = ctk.CTkTabview(root)
    tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    atom = tabs.add("Atom")
    molecule = tabs.add("Molecule")
    trial = tabs.add("Trial")
    root._ml_tabs = tabs  # type: ignore[attr-defined]

    # Atom
    atom_frame = ctk.CTkFrame(atom, fg_color="transparent")
    atom_frame.pack(fill="both", expand=True, padx=8, pady=8)
    atom_bar = ctk.CTkFrame(atom_frame, fg_color="transparent")
    atom_bar.pack(fill="x", pady=(0, 6))
    ctk.CTkButton(
        atom_bar,
        text="Open Atom Create (Deck)",
        width=180,
        command=(on_open_atom_create or (lambda: None)),
        state="normal" if on_open_atom_create else "disabled",
    ).pack(side="left")
    ctk.CTkButton(
        atom_bar,
        text="Compose molecules →",
        width=160,
        fg_color="#2A3140",
        hover_color="#3A4558",
        command=(on_goto_molecule_tab or (lambda: None)),
        state="normal" if on_goto_molecule_tab else "disabled",
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        atom_bar,
        text="Trial →",
        width=80,
        fg_color="#2A3140",
        hover_color="#3A4558",
        command=(on_goto_trial_tab or (lambda: None)),
        state="normal" if on_goto_trial_tab else "disabled",
    ).pack(side="left", padx=(8, 0))
    ctk.CTkLabel(
        atom_bar,
        text="LOL actuations must show as atoms below — no silent gaps",
        text_color="#7E8796",
    ).pack(side="left", padx=(12, 0))
    atom_host = ctk.CTkFrame(atom_frame, fg_color="transparent")
    atom_host.pack(fill="both", expand=True)
    if host_atom_pane is not None:
        host_atom_pane(atom_host)
    else:
        ctk.CTkLabel(
            atom_host,
            text="Atom library + LOL coverage mounts when App wires Molecule Lab.",
            text_color="#9AA4B2",
        ).pack(anchor="w", pady=12)

    # Molecule — in-tab composer (float still available)
    mol_frame = ctk.CTkFrame(molecule, fg_color="transparent")
    mol_frame.pack(fill="both", expand=True, padx=8, pady=8)
    toolbar = ctk.CTkFrame(mol_frame, fg_color="transparent")
    toolbar.pack(fill="x", pady=(0, 6))
    ctk.CTkButton(
        toolbar,
        text="Pop out composer",
        width=140,
        command=(on_open_composer or (lambda: None)),
        state="normal" if on_open_composer else "disabled",
    ).pack(side="left")
    ctk.CTkButton(
        toolbar,
        text="Trial →",
        width=80,
        fg_color="#2A3140",
        hover_color="#3A4558",
        command=(on_goto_trial_tab or (lambda: None)),
        state="normal" if on_goto_trial_tab else "disabled",
    ).pack(side="left", padx=(8, 0))
    ctk.CTkLabel(
        toolbar,
        text="Compose here · Trial runs packs · Pop out for a floating Lab",
        text_color="#7E8796",
    ).pack(side="left", padx=(12, 0))
    composer_host = ctk.CTkFrame(mol_frame, fg_color="transparent")
    composer_host.pack(fill="both", expand=True)
    if host_composer is not None:
        host_composer(composer_host)
    else:
        ctk.CTkLabel(
            composer_host,
            text="In-tab composer mounts when App wires Molecule Lab.",
            text_color="#9AA4B2",
        ).pack(anchor="w", pady=12)

    # Trial — browse / Start / Dry-run / Walkthrough
    trial_frame = ctk.CTkFrame(trial, fg_color="transparent")
    trial_frame.pack(fill="both", expand=True, padx=8, pady=8)
    trial_bar = ctk.CTkFrame(trial_frame, fg_color="transparent")
    trial_bar.pack(fill="x", pady=(0, 6))
    ctk.CTkLabel(
        trial_bar,
        text="Run selected atoms / molecules · Dry-run · Walkthrough",
        text_color="#7E8796",
        anchor="w",
    ).pack(side="left")
    trial_host = ctk.CTkFrame(trial_frame, fg_color="transparent")
    trial_host.pack(fill="both", expand=True)
    if host_automations is not None:
        host_automations(trial_host)
    else:
        ctk.CTkLabel(
            trial_host,
            text="Trial panel mounts when App wires Molecule Lab.",
            text_color="#9AA4B2",
        ).pack(anchor="w", pady=12)
    return root


class AtomLabPane(ctk.CTkFrame):
    """Atom library + LOL coverage board."""

    def __init__(
        self,
        master,
        *,
        get_library_rows: Callable[[], list[dict[str, Any]]],
        get_coverage_rows: Callable[[], list[Any]],
        on_refresh: Callable[[], None],
        on_seed_missing: Callable[[], None],
        on_run_atom: Callable[[str], None],
        on_create_stub: Callable[[str], None] | None = None,
    ) -> None:
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

    def _build(self) -> None:
        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(tools, text="Refresh", width=90, command=self._refresh_clicked).pack(
            side="left"
        )
        ctk.CTkButton(
            tools,
            text="Seed missing LOL wrappers",
            width=180,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._seed_clicked,
        ).pack(side="left", padx=(8, 0))
        self.run_btn = ctk.CTkButton(
            tools,
            text="Run selected once",
            width=140,
            command=self._run_clicked,
            state="disabled",
        )
        self.run_btn.pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1, uniform="ml")
        body.grid_columnconfigure(1, weight=1, uniform="ml")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(left, text="Atom library", font=ctk.CTkFont(weight="bold"), anchor="w").pack(
            anchor="w", padx=8, pady=(8, 2)
        )
        self.lib_list = ctk.CTkScrollableFrame(left, height=360)
        self.lib_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        right = ctk.CTkFrame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(
            right, text="LOL coverage", font=ctk.CTkFont(weight="bold"), anchor="w"
        ).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(
            right,
            text="Green = atom exists · Amber = seed · Gray = LOL-only chrome",
            text_color="#7E8796",
            anchor="w",
        ).pack(anchor="w", padx=8)
        self.cov_list = ctk.CTkScrollableFrame(right, height=360)
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
            fg_color="#1F2A3A" if selected else "transparent",
            command=lambda i=eid: self._select(i),
        )
        btn.pack(fill="x")
        ctk.CTkLabel(
            frame,
            text=f"{eid} · {enabled} · {tags}{ghost}",
            anchor="w",
            text_color="#9AA4B2",
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
