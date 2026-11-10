"""Molecule Lab — browse, compose, reorder, and condition molecules."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from idle_lab import win32_api
from idle_lab.composer.catalog import CapabilityCatalog, load_capability_catalog
from idle_lab.composer.expand import (
    ComposerExpandError,
    expand_and_write,
    load_draft,
    load_library,
    preview_expansion,
)
from idle_lab.composer.lco_placement import load_placements, set_enabled
from idle_lab.composer.model import (
    KIND_LABELS,
    PHASE_LABELS,
    PHASE_ORDER,
    ComposerContext,
    ComposerDraft,
    ConditionAny,
    ConditionLeaf,
    DraftStep,
    PaletteItem,
    StepCondition,
    build_palette,
    outputs_for_step,
)
from idle_lab.presets import project_root


_BG = "#141A22"
_PANEL = "#1B2330"
_MUTED = "#7E8796"
_ACCENT = "#9FD4F0"
_TEXT = "#E8EEF6"
_SELECT = "#3A5A78"


class MoleculeLabWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        automations_root: Path | None = None,
        project_root_path: Path | None = None,
        on_exported: Callable[[str], None] | None = None,
        on_status: Callable[[str, str], None] | None = None,
        on_lco_changed: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Molecule Lab")
        self.geometry("1280x860")
        self.minsize(1100, 720)
        self.configure(fg_color=_BG)
        self.automations_root = Path(automations_root or (project_root() / "automations"))
        self.project_root_path = Path(project_root_path or project_root())
        self.on_exported = on_exported
        self.on_status = on_status
        self.on_lco_changed = on_lco_changed
        self.on_close = on_close

        self.catalog: CapabilityCatalog = load_capability_catalog(self.project_root_path)
        self.context = ComposerContext()
        self.draft = ComposerDraft()
        self._library: list[dict] = []
        self._lco_by_id: dict[str, object] = {}
        self._palette_items: list[PaletteItem] = []
        self._selected_step: int | None = None
        self._library_filter_phase = ctk.StringVar(value="all")

        self._build()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self._close)
        # Orphan + focus like LCO console / flight deck — owned Toplevels under a
        # withdrawn Lab never receive Win32 keyboard focus, so entries look dead.
        self.after(0, self._orphan_and_focus)
        self.after(50, self._orphan_and_focus)
        self.after(150, self._orphan_and_focus)

    # --- lifecycle ---------------------------------------------------------

    def _orphan_and_focus(self) -> None:
        """Detach from Lab's Win32 owner and steal keyboard focus into this window."""

        if not self.winfo_exists():
            return
        try:
            self.update_idletasks()
            hwnd = win32_api.widget_hwnd(self)
            win32_api.clear_window_owner(hwnd)
            self.lift()
            self.attributes("-topmost", True)
            self.focus_force()
            win32_api.focus_window(hwnd)
        except Exception:
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass
        try:
            self.after(300, self._release_topmost)
        except Exception:
            pass

    def _release_topmost(self) -> None:
        try:
            if self.winfo_exists():
                self.attributes("-topmost", False)
        except Exception:
            pass

    def _close(self) -> None:
        callback = self.on_close
        try:
            self.destroy()
        except Exception:
            pass
        if callback is not None:
            try:
                callback()
            except Exception:
                pass

    def _emit(self, message: str, level: str = "info") -> None:
        if self.on_status:
            try:
                self.on_status(message, level)
            except Exception:
                pass
        self.status_var.set(message)

    # --- build -------------------------------------------------------------

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            header,
            text="Molecule Lab",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=_ACCENT,
        ).pack(side="left")
        self.context_var = ctk.StringVar(value="Context: (choose a tab)")
        ctk.CTkLabel(header, textvariable=self.context_var, text_color=_MUTED).pack(side="right")

        ctk.CTkLabel(
            self,
            text=(
                "Click palette items to add them. Select a step to edit conditions "
                "(previous-step sources). Save as JSON. Library is grouped by phase."
            ),
            text_color=_MUTED,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=14, pady=(0, 8))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=3)
        body.grid_columnconfigure(3, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self._build_library(body)
        self._build_palette(body)
        self._build_draft(body)
        self._build_inspect(body)
        self._build_footer()

    def _build_library(self, body: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(frame, text="Library", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        filt = ctk.CTkFrame(frame, fg_color="transparent")
        filt.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkOptionMenu(
            filt,
            variable=self._library_filter_phase,
            values=["all", *PHASE_ORDER],
            width=120,
            command=lambda _v: self._render_library(),
        ).pack(side="left")
        ctk.CTkButton(filt, text="New", width=60, command=self._new_draft).pack(side="right")
        self.library_list = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.library_list.pack(fill="both", expand=True, padx=6, pady=(0, 10))

    def _build_palette(self, body: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        frame.grid(row=0, column=1, sticky="nsew", padx=6)
        ctk.CTkLabel(frame, text="Palette (click = add)", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        self.palette_list = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.palette_list.pack(fill="both", expand=True, padx=6, pady=(0, 10))

    def _build_draft(self, body: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        frame.grid(row=0, column=2, sticky="nsew", padx=6)
        ctk.CTkLabel(frame, text="Draft", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )

        meta = ctk.CTkFrame(frame, fg_color="transparent")
        meta.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(meta, text="Title", text_color=_MUTED, width=36).pack(side="left")
        self.title_entry = ctk.CTkEntry(meta, text_color=_TEXT)
        self.title_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.title_entry.insert(0, self.draft.title)
        self.title_entry.bind("<KeyRelease>", lambda _e: self._sync_meta())

        meta2 = ctk.CTkFrame(frame, fg_color="transparent")
        meta2.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(meta2, text="Phase", text_color=_MUTED, width=36).pack(side="left")
        self.phase_var = ctk.StringVar(value=self.draft.phase)
        ctk.CTkOptionMenu(
            meta2,
            variable=self.phase_var,
            values=list(PHASE_ORDER),
            width=110,
            command=lambda _v: self._sync_meta(),
        ).pack(side="left", padx=(4, 8))
        ctk.CTkLabel(meta2, text="Kind", text_color=_MUTED).pack(side="left")
        self.kind_var = ctk.StringVar(value=self.draft.kind)
        ctk.CTkOptionMenu(
            meta2,
            variable=self.kind_var,
            values=list(KIND_LABELS.keys()),
            width=110,
            command=lambda _v: self._sync_meta(),
        ).pack(side="left", padx=(4, 0))

        self.steps_list = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.steps_list.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        step_btns = ctk.CTkFrame(frame, fg_color="transparent")
        step_btns.pack(fill="x", padx=10, pady=(0, 10))
        for label, cmd, w in (
            ("↑", self._move_up, 36),
            ("↓", self._move_down, 36),
            ("Remove", self._remove_selected, 70),
            ("Clear", self._clear_draft, 60),
        ):
            ctk.CTkButton(
                step_btns,
                text=label,
                width=w,
                fg_color="#2A3140",
                command=cmd,
            ).pack(side="left", padx=(0, 4))

    def _build_inspect(self, body: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        frame.grid(row=0, column=3, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(frame, text="Expansion preview", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        self.preview = ctk.CTkTextbox(
            frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=_TEXT,
            fg_color="#121820",
            height=160,
        )
        self.preview.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        ctk.CTkLabel(frame, text="Conditions", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(0, 4)
        )
        self.cond_hint = ctk.CTkLabel(
            frame,
            text="Select a draft step to edit its conditions.",
            text_color=_MUTED,
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self.cond_hint.pack(fill="x", padx=10, pady=(0, 6))

        self.cond_panel = ctk.CTkFrame(frame, fg_color="transparent")
        # Packed only when a step is selected.

        pol = ctk.CTkFrame(self.cond_panel, fg_color="transparent")
        pol.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(pol, text="When true", text_color=_MUTED, width=72).pack(side="left")
        self.cond_when = ctk.StringVar(value="perform")
        ctk.CTkOptionMenu(
            pol,
            variable=self.cond_when,
            values=["perform", "skip"],
            width=120,
            command=lambda _v: self._apply_polarity(),
        ).pack(side="left", padx=(4, 0))

        self.cond_list = ctk.CTkScrollableFrame(self.cond_panel, fg_color="#121820", height=180)
        self.cond_list.pack(fill="both", expand=True, pady=(0, 6))

        add_row = ctk.CTkFrame(self.cond_panel, fg_color="transparent")
        add_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(add_row, text="Source", text_color=_MUTED, width=52).pack(side="left")
        self.cond_source = ctk.StringVar(value="")
        self.cond_source_menu = ctk.CTkOptionMenu(
            add_row,
            variable=self.cond_source,
            values=["(none)"],
            width=160,
            command=lambda _v: self._on_source_changed(),
        )
        self.cond_source_menu.pack(side="left", padx=(4, 0))

        field_row = ctk.CTkFrame(self.cond_panel, fg_color="transparent")
        field_row.pack(fill="x", pady=2)
        ctk.CTkLabel(field_row, text="Field", text_color=_MUTED, width=52).pack(side="left")
        self.cond_field = ctk.StringVar(value="completed")
        self.cond_field_menu = ctk.CTkOptionMenu(
            field_row,
            variable=self.cond_field,
            values=["completed"],
            width=160,
        )
        self.cond_field_menu.pack(side="left", padx=(4, 0))

        op_row = ctk.CTkFrame(self.cond_panel, fg_color="transparent")
        op_row.pack(fill="x", pady=2)
        ctk.CTkLabel(op_row, text="Op", text_color=_MUTED, width=52).pack(side="left")
        self.cond_op = ctk.StringVar(value="gte")
        ctk.CTkOptionMenu(
            op_row,
            variable=self.cond_op,
            values=["gte", "lte", "gt", "lt", "eq", "between", "nonempty"],
            width=100,
            command=lambda _v: self._sync_value_entries(),
        ).pack(side="left", padx=(4, 8))
        self.cond_value = ctk.CTkEntry(op_row, width=64, placeholder_text="value")
        self.cond_value.pack(side="left", padx=(0, 4))
        self.cond_value_hi = ctk.CTkEntry(op_row, width=64, placeholder_text="hi")
        self.cond_value_hi.pack(side="left")

        btn_row = ctk.CTkFrame(self.cond_panel, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(
            btn_row,
            text="Add condition",
            width=110,
            fg_color="#2F6F5E",
            hover_color="#3A8A74",
            command=self._add_condition_leaf,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row,
            text="Add OR group",
            width=110,
            fg_color="#2A3140",
            command=self._add_or_group,
        ).pack(side="left")

        self.detail_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            frame,
            textvariable=self.detail_var,
            text_color=_MUTED,
            wraplength=280,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 10))

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=14, pady=(0, 12))
        self.status_var = ctk.StringVar(value=f"Catalog: {self.catalog.source}")
        ctk.CTkLabel(footer, textvariable=self.status_var, text_color=_MUTED, anchor="w").pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            footer,
            text="Save molecule",
            width=130,
            fg_color="#2F6F5E",
            hover_color="#3A8A74",
            command=self._save,
        ).pack(side="right")
        ctk.CTkButton(
            footer,
            text="Refresh",
            width=90,
            fg_color="#2A3140",
            command=self._reload_catalog,
        ).pack(side="right", padx=(0, 8))

    # --- sync / refresh ----------------------------------------------------

    def _sync_meta(self) -> None:
        self.draft.title = self.title_entry.get().strip() or "Untitled molecule"
        phase = self.phase_var.get()
        kind = self.kind_var.get()
        if phase in PHASE_LABELS:
            self.draft.phase = phase  # type: ignore[assignment]
        if kind in KIND_LABELS:
            self.draft.kind = kind  # type: ignore[assignment]
        self._render_preview()

    def _reload_catalog(self) -> None:
        self.catalog = load_capability_catalog(self.project_root_path)
        self.refresh()
        self._emit("Catalog + library refreshed.", "ok")

    def refresh(self) -> None:
        self._library = load_library(self.automations_root)
        self._lco_by_id = {p.molecule_id: p for p in load_placements(self.automations_root)}
        self._palette_items = build_palette(
            context=self.context,
            tabs=self.catalog.tabs,
            library=self._library,
            exclude_molecule_id=self.draft.collection_id,
        )
        tab = self.context.tab
        if tab:
            caps = self.catalog.tabs.get(tab)
            label = caps.label if caps else tab
            hot = f" [{caps.hotkey}]" if caps and caps.hotkey else ""
            self.context_var.set(f"Context: {label}{hot}")
        else:
            self.context_var.set("Context: (choose a tab)")
        self._render_library()
        self._render_palette()
        self._render_steps()
        self._render_condition_panel()
        self._render_preview()

    # --- library -----------------------------------------------------------

    def _render_library(self) -> None:
        for child in self.library_list.winfo_children():
            child.destroy()
        filt = self._library_filter_phase.get()
        grouped: dict[str, list[dict]] = {p: [] for p in PHASE_ORDER}
        for mol in self._library:
            phase = str(mol.get("phase") or "unfiled")
            if phase not in grouped:
                phase = "unfiled"
            if filt != "all" and phase != filt:
                continue
            grouped[phase].append(mol)
        for phase in PHASE_ORDER:
            moles = grouped.get(phase) or []
            if filt == "all" and not moles:
                continue
            ctk.CTkLabel(
                self.library_list,
                text=PHASE_LABELS.get(phase, phase),
                text_color=_ACCENT,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=4, pady=(8, 2))
            if not moles:
                ctk.CTkLabel(self.library_list, text="(empty)", text_color=_MUTED).pack(
                    anchor="w", padx=8
                )
                continue
            for mol in moles:
                kind = str(mol.get("kind") or "buy")
                title = str(mol.get("title") or mol.get("id"))
                mol_id = str(mol.get("id"))
                row = ctk.CTkFrame(self.library_list, fg_color="transparent")
                row.pack(fill="x", padx=2, pady=2)
                place = self._lco_by_id.get(mol_id)
                enabled = bool(getattr(place, "enabled", False)) if place else False
                hotkey = getattr(place, "hotkey", None) if place else None
                var = ctk.BooleanVar(value=enabled)
                switch = ctk.CTkSwitch(row, text="", variable=var, width=36)
                switch.configure(
                    command=lambda mid=mol_id, t=title, v=var: self._set_lco_enabled(mid, t, bool(v.get()))
                )
                switch.pack(side="left", padx=(2, 4))
                hk = f"[{hotkey}] " if enabled and hotkey else ""
                ctk.CTkButton(
                    row,
                    text=f"{hk}{title}  ·  {KIND_LABELS.get(kind, kind)}",
                    anchor="w",
                    fg_color="#243041",
                    hover_color="#314257",
                    command=lambda mid=mol_id: self._open_library_molecule(mid),
                ).pack(side="left", fill="x", expand=True)

    def _set_lco_enabled(self, mol_id: str, title: str, enabled: bool) -> None:
        updated = set_enabled(
            self.automations_root,
            mol_id,
            enabled=enabled,
            title=title,
        )
        self._lco_by_id[mol_id] = updated
        self._render_library()
        if updated.enabled:
            self._emit(f"LCO on for “{title}” → [{updated.hotkey}]", "ok")
        else:
            self._emit(f"LCO off for “{title}” (position kept).", "info")
        if self.on_lco_changed:
            try:
                self.on_lco_changed()
            except Exception:
                pass

    def _open_library_molecule(self, mol_id: str) -> None:
        draft = load_draft(self.automations_root, mol_id)
        if draft is not None:
            self.draft = draft
            self._load_draft_into_form()
            self.context.clear()
            if self.draft.requires_tab:
                self.context.enter_tab(self.draft.requires_tab)
            self.refresh()
            self._emit(f"Editing draft for “{mol_id}”.", "ok")
            return
        # No draft IR — start a composite that references it.
        mol = next((m for m in self._library if str(m.get("id")) == mol_id), None)
        if mol is None:
            self._emit(f"Molecule not found: {mol_id}", "warn")
            return
        self.draft = ComposerDraft(
            title=f"Edit of {mol.get('title') or mol_id}",
            phase=str(mol.get("phase") or "unfiled"),  # type: ignore[arg-type]
            kind=str(mol.get("kind") or "composite"),  # type: ignore[arg-type]
        )
        if self.draft.phase not in PHASE_LABELS:
            self.draft.phase = "unfiled"
        if self.draft.kind not in KIND_LABELS:
            self.draft.kind = "composite"
        self.draft.add_step(
            DraftStep(
                kind="molecule_ref",
                label=str(mol.get("title") or mol_id),
                molecule_id=mol_id,
                tab=(str(mol["requires_tab"]) if mol.get("requires_tab") else None),
                detail="Opened from library without a Lab draft — nested as a reference.",
            )
        )
        self._load_draft_into_form()
        self.context.clear()
        self.refresh()
        self._emit(
            f"No Lab draft for “{mol_id}” — nested as a reference you can condition/reorder.",
            "warn",
        )

    def _load_draft_into_form(self) -> None:
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, self.draft.title)
        self.phase_var.set(self.draft.phase)
        self.kind_var.set(self.draft.kind)
        self._selected_step = None

    def _new_draft(self) -> None:
        self.draft = ComposerDraft()
        self.context.clear()
        self._load_draft_into_form()
        self.refresh()
        self._emit("New blank molecule.", "ok")

    # --- palette -----------------------------------------------------------

    def _render_palette(self) -> None:
        for child in self.palette_list.winfo_children():
            child.destroy()
        current_group = None
        for i, item in enumerate(self._palette_items):
            if item.group != current_group:
                current_group = item.group
                ctk.CTkLabel(
                    self.palette_list,
                    text=current_group,
                    text_color=_ACCENT,
                    font=ctk.CTkFont(size=12, weight="bold"),
                ).pack(anchor="w", padx=4, pady=(8, 2))
            ctk.CTkButton(
                self.palette_list,
                text=item.label,
                anchor="w",
                fg_color="#243041",
                hover_color="#314257",
                command=lambda idx=i: self._palette_clicked(idx),
            ).pack(fill="x", padx=4, pady=2)

    def _palette_clicked(self, index: int) -> None:
        if not (0 <= index < len(self._palette_items)):
            return
        item = self._palette_items[index]
        self.detail_var.set(item.detail)
        if item.key == "ctx:clear_tab":
            self.context.clear()
            self.refresh()
            self._emit("Left tab context.", "info")
            return
        # Every other click adds (tabs also enter context).
        self._apply_palette_item(item)

    def _apply_palette_item(self, item: PaletteItem) -> None:
        if item.kind == "ensure_tab" and item.tab:
            self.context.enter_tab(item.tab)
            already = any(s.kind == "ensure_tab" and s.tab == item.tab for s in self.draft.steps)
            if not already:
                self.draft.add_step(
                    DraftStep(
                        kind="ensure_tab",
                        label=item.label,
                        tab=item.tab,
                        detail=item.detail,
                    )
                )
            self.refresh()
            self._emit(f"Context → {item.tab}. Upgrades unlocked — click to add.", "ok")
            return

        if item.kind == "seek_and_buy":
            self.draft.add_step(
                DraftStep(
                    kind="seek_and_buy",
                    label=item.label,
                    tab=item.tab,
                    catalog_id=item.catalog_id,
                    catalog_index=item.catalog_index,
                    guards=item.guards,
                    detail=item.detail,
                )
            )
            self.refresh()
            self._select_step(len(self.draft.steps) - 1)
            self._emit(f"Added: {item.label}", "ok")
            return

        if item.kind == "molecule_ref":
            self.draft.add_step(
                DraftStep(
                    kind="molecule_ref",
                    label=item.label,
                    tab=item.tab,
                    molecule_id=item.molecule_id,
                    detail=item.detail,
                )
            )
            self.refresh()
            self._select_step(len(self.draft.steps) - 1)
            self._emit(f"Added molecule: {item.label}", "ok")
            return

        if item.kind == "event_ref":
            self.draft.add_step(
                DraftStep(
                    kind="event_ref",
                    label=item.label,
                    event_id=item.event_id,
                    detail=item.detail,
                )
            )
            self.refresh()
            self._select_step(len(self.draft.steps) - 1)
            self._emit(f"Added atom: {item.label}", "ok")
            return

    # --- draft steps -------------------------------------------------------

    def _render_steps(self) -> None:
        for child in self.steps_list.winfo_children():
            child.destroy()
        if not self.draft.steps:
            ctk.CTkLabel(
                self.steps_list,
                text="Empty — click a tab, then upgrades.",
                text_color=_MUTED,
            ).pack(anchor="w", padx=6, pady=8)
            return
        for i, step in enumerate(self.draft.steps):
            selected = self._selected_step == i
            btn = ctk.CTkButton(
                self.steps_list,
                text=f"{i + 1}. {step.display_label()}",
                anchor="w",
                fg_color=_SELECT if selected else "#243041",
                hover_color="#314257",
                command=lambda idx=i: self._select_step(idx),
            )
            btn.pack(fill="x", padx=4, pady=2)

    def _select_step(self, index: int) -> None:
        self._selected_step = index
        self._render_steps()
        if not (0 <= index < len(self.draft.steps)):
            self.detail_var.set("")
            self._render_condition_panel()
            return
        step = self.draft.steps[index]
        detail = step.detail
        if step.guards:
            down = ", ".join(step.guards.too_far_down) or "—"
            up = ", ".join(step.guards.too_far_up) or "—"
            detail = f"{detail}\n\nToo far up: {up}\nToo far down: {down}"
        self.detail_var.set(detail)
        self._render_condition_panel()
        self._render_preview()

    def _render_condition_panel(self) -> None:
        idx = self._selected_step
        if idx is None or not (0 <= idx < len(self.draft.steps)):
            try:
                self.cond_panel.pack_forget()
            except Exception:
                pass
            self.cond_hint.configure(text="Select a draft step to edit its conditions.")
            try:
                self.cond_hint.pack(fill="x", padx=10, pady=(0, 6))
            except Exception:
                pass
            return
        try:
            self.cond_hint.pack_forget()
        except Exception:
            pass
        if not self.cond_panel.winfo_ismapped():
            self.cond_panel.pack(fill="both", expand=False, padx=10, pady=(0, 4))

        step = self.draft.steps[idx]
        gate = step.condition
        self.cond_when.set(gate.when_true if gate else "perform")
        self._refresh_source_options(idx)
        self._on_source_changed()
        self._sync_value_entries()
        self._render_condition_list(gate)

    def _refresh_source_options(self, step_index: int) -> None:
        labels: list[str] = []
        for i in range(step_index):
            prev = self.draft.steps[i]
            labels.append(f"{i + 1}. {prev.label}")
        if not labels:
            labels = ["(no previous step)"]
        current = self.cond_source.get()
        try:
            self.cond_source_menu.configure(values=labels)
        except Exception:
            pass
        if current in labels and not current.startswith("("):
            self.cond_source.set(current)
        else:
            self.cond_source.set(labels[0])

    def _source_index(self) -> int | None:
        raw = self.cond_source.get()
        if not raw or raw.startswith("("):
            return None
        try:
            return int(raw.split(".", 1)[0].strip()) - 1
        except ValueError:
            return None

    def _on_source_changed(self) -> None:
        src = self._source_index()
        fields = ["completed"]
        if src is not None and 0 <= src < len(self.draft.steps):
            fields = outputs_for_step(self.draft.steps[src]) or ["completed"]
        try:
            self.cond_field_menu.configure(values=fields)
        except Exception:
            pass
        if self.cond_field.get() not in fields:
            self.cond_field.set(fields[0])

    def _sync_value_entries(self) -> None:
        op = self.cond_op.get()
        if op == "nonempty":
            self.cond_value.configure(state="disabled")
            self.cond_value_hi.configure(state="disabled")
        elif op == "between":
            self.cond_value.configure(state="normal")
            self.cond_value_hi.configure(state="normal")
        else:
            self.cond_value.configure(state="normal")
            self.cond_value_hi.configure(state="disabled")

    def _parse_entry_num(self, entry: ctk.CTkEntry) -> float | None:
        raw = entry.get().strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def _ensure_gate(self) -> StepCondition | None:
        if self._selected_step is None or not (0 <= self._selected_step < len(self.draft.steps)):
            return None
        step = self.draft.steps[self._selected_step]
        if step.condition is None:
            step.condition = StepCondition(when_true=self.cond_when.get() or "perform")  # type: ignore[arg-type]
        return step.condition

    def _apply_polarity(self) -> None:
        gate = self._ensure_gate()
        if gate is None:
            return
        when = self.cond_when.get()
        if when not in {"perform", "skip"}:
            when = "perform"
        gate.when_true = when  # type: ignore[assignment]
        if gate.is_empty():
            self.draft.steps[self._selected_step].condition = None  # type: ignore[index]
        self._render_steps()
        self._render_preview()

    def _build_leaf_from_form(self) -> ConditionLeaf | None:
        src = self._source_index()
        if src is None or self._selected_step is None or src >= self._selected_step:
            self._emit("Pick a previous step as the condition source.", "warn")
            return None
        op = self.cond_op.get()
        value = self._parse_entry_num(self.cond_value)
        value_hi = self._parse_entry_num(self.cond_value_hi)
        if op != "nonempty" and value is None and op != "between":
            self._emit("Enter a numeric value for this condition.", "warn")
            return None
        if op == "between" and (value is None or value_hi is None):
            self._emit("Between needs both low and high values.", "warn")
            return None
        return ConditionLeaf(
            source_step=src,
            field=self.cond_field.get() or "completed",
            op=op,  # type: ignore[arg-type]
            value=value,
            value_hi=value_hi if op == "between" else None,
        )

    def _add_condition_leaf(self) -> None:
        leaf = self._build_leaf_from_form()
        if leaf is None:
            return
        gate = self._ensure_gate()
        if gate is None:
            return
        gate.when_true = self.cond_when.get() if self.cond_when.get() in {"perform", "skip"} else "perform"  # type: ignore[assignment]
        gate.all.append(leaf)
        self._render_condition_list(gate)
        self._render_steps()
        self._render_preview()

    def _add_or_group(self) -> None:
        """Add an OR group: current form leaf + a completed-check on the same source."""

        leaf_a = self._build_leaf_from_form()
        if leaf_a is None:
            return
        # Second arm defaults to completed/nonempty on the same source so the group is valid.
        leaf_b = ConditionLeaf(
            source_step=leaf_a.source_step,
            field="completed",
            op="nonempty",
        )
        if leaf_a.field == "completed" and leaf_a.op == "nonempty":
            # Avoid identical arms — use first catalog field with gte 1 if possible.
            fields = outputs_for_step(self.draft.steps[leaf_a.source_step])
            alt = next((f for f in fields if f != "completed"), None)
            if alt is None:
                self._emit("Need two distinct predicates for an OR group — change field/op first.", "warn")
                return
            leaf_b = ConditionLeaf(source_step=leaf_a.source_step, field=alt, op="nonempty")
        gate = self._ensure_gate()
        if gate is None:
            return
        gate.when_true = self.cond_when.get() if self.cond_when.get() in {"perform", "skip"} else "perform"  # type: ignore[assignment]
        gate.all.append(ConditionAny(leaves=[leaf_a, leaf_b]))
        self._emit("OR group added — remove an arm or edit JSON later if needed.", "ok")
        self._render_condition_list(gate)
        self._render_steps()
        self._render_preview()

    def _remove_clause(self, clause_index: int) -> None:
        if self._selected_step is None or not (0 <= self._selected_step < len(self.draft.steps)):
            return
        step = self.draft.steps[self._selected_step]
        gate = step.condition
        if gate is None or not (0 <= clause_index < len(gate.all)):
            return
        gate.all.pop(clause_index)
        if gate.is_empty():
            step.condition = None
            gate = None
        self._render_condition_list(gate)
        self._render_steps()
        self._render_preview()

    def _render_condition_list(self, gate: StepCondition | None) -> None:
        for child in self.cond_list.winfo_children():
            child.destroy()
        if gate is None or gate.is_empty():
            ctk.CTkLabel(
                self.cond_list,
                text="No conditions — step always runs (until runtime C5).",
                text_color=_MUTED,
                anchor="w",
            ).pack(fill="x", padx=4, pady=4)
            return
        for i, clause in enumerate(gate.all):
            row = ctk.CTkFrame(self.cond_list, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=2)
            label = clause.summary()
            if isinstance(clause, ConditionAny):
                prefix = "OR"
            else:
                prefix = "AND" if i > 0 else "IF"
            ctk.CTkLabel(
                row,
                text=f"{prefix} {label}",
                anchor="w",
                text_color=_TEXT,
                wraplength=220,
                justify="left",
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row,
                text="×",
                width=28,
                fg_color="#3A2A2A",
                hover_color="#5A3A3A",
                command=lambda idx=i: self._remove_clause(idx),
            ).pack(side="right")

    def _move_up(self) -> None:
        if self._selected_step is None:
            return
        dest = self.draft.move_step(self._selected_step, -1)
        if dest is not None:
            self._selected_step = dest
            self.refresh()
            self._select_step(dest)

    def _move_down(self) -> None:
        if self._selected_step is None:
            return
        dest = self.draft.move_step(self._selected_step, 1)
        if dest is not None:
            self._selected_step = dest
            self.refresh()
            self._select_step(dest)

    def _remove_selected(self) -> None:
        if self._selected_step is None:
            self._emit("Select a draft step to remove.", "warn")
            return
        self.draft.remove_at(self._selected_step)
        self._selected_step = None
        self.refresh()

    def _clear_draft(self) -> None:
        self.draft.clear_steps()
        self.draft.title = "Untitled molecule"
        self.draft.phase = "unfiled"
        self.draft.kind = "buy"
        self.draft.collection_id = None
        self._load_draft_into_form()
        self.context.clear()
        self.refresh()

    def _render_preview(self) -> None:
        lines = preview_expansion(self.draft, self.catalog)
        try:
            self.preview.configure(state="normal")
        except Exception:
            pass
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "\n".join(lines))

    def _save(self) -> None:
        self._sync_meta()
        try:
            result = expand_and_write(
                self.draft,
                automations_root=self.automations_root,
                catalog=self.catalog,
            )
        except ComposerExpandError as exc:
            self._emit(str(exc), "warn")
            return
        except Exception as exc:
            self._emit(f"Export failed: {exc}", "error")
            return
        self.draft.collection_id = result.collection_id
        msg = (
            f"Saved “{result.collection_id}” "
            f"({len(result.event_paths)} atom file(s)). Reload Loops to pick it up."
        )
        self._emit(msg, "ok")
        self._render_preview()
        if self.on_exported:
            try:
                self.on_exported(result.collection_id)
            except Exception:
                pass
        self.refresh()


# Back-compat for app wiring / older imports.
MoleculeComposerWindow = MoleculeLabWindow
