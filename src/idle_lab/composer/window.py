"""Molecule Composer window — context-gated palette → draft → export JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk

from idle_lab.composer.catalog import CapabilityCatalog, load_capability_catalog
from idle_lab.composer.expand import (
    ComposerExpandError,
    expand_and_write,
    load_library,
    preview_expansion,
)
from idle_lab.composer.model import (
    ComposerContext,
    ComposerDraft,
    DraftStep,
    PaletteItem,
    build_palette,
)
from idle_lab.presets import project_root


_BG = "#141A22"
_PANEL = "#1B2330"
_MUTED = "#7E8796"
_ACCENT = "#9FD4F0"


class MoleculeComposerWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        automations_root: Path | None = None,
        project_root_path: Path | None = None,
        on_exported: Callable[[str], None] | None = None,
        on_status: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Molecule Composer")
        self.geometry("920x620")
        self.minsize(760, 480)
        self.configure(fg_color=_BG)
        self.automations_root = Path(automations_root or (project_root() / "automations"))
        self.project_root_path = Path(project_root_path or project_root())
        self.on_exported = on_exported
        self.on_status = on_status

        self.catalog: CapabilityCatalog = load_capability_catalog(self.project_root_path)
        self.context = ComposerContext()
        self.draft = ComposerDraft()
        self._palette_items: list[PaletteItem] = []
        self._selected_palette: int | None = None
        self._selected_step: int | None = None

        self._build()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(50, self._lift)

    def _lift(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _close(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass

    def _emit(self, message: str, level: str = "info") -> None:
        if self.on_status:
            try:
                self.on_status(message, level)
            except Exception:
                pass
        self.status_var.set(message)

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            header,
            text="Molecule Composer",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=_ACCENT,
        ).pack(side="left")
        self.context_var = ctk.StringVar(value="Context: (choose a tab)")
        ctk.CTkLabel(header, textvariable=self.context_var, text_color=_MUTED).pack(
            side="right"
        )

        ctk.CTkLabel(
            self,
            text="Only legal actions show. Pick a tab → upgrades + saved molecules for that tab appear.",
            text_color=_MUTED,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=14, pady=(0, 8))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Palette
        left = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(left, text="Palette", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        self.palette_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.palette_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.add_button = ctk.CTkButton(left, text="Add to draft", command=self._add_selected)
        self.add_button.pack(fill="x", padx=10, pady=(0, 10))

        # Draft
        mid = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        mid.grid(row=0, column=1, sticky="nsew", padx=6)
        ctk.CTkLabel(mid, text="Draft molecule", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        title_row = ctk.CTkFrame(mid, fg_color="transparent")
        title_row.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(title_row, text="Title", text_color=_MUTED, width=40).pack(side="left")
        self.title_entry = ctk.CTkEntry(title_row)
        self.title_entry.pack(side="left", fill="x", expand=True)
        self.title_entry.insert(0, self.draft.title)
        self.title_entry.bind("<KeyRelease>", lambda _e: self._sync_title())

        self.steps_list = ctk.CTkScrollableFrame(mid, fg_color="transparent")
        self.steps_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        step_btns = ctk.CTkFrame(mid, fg_color="transparent")
        step_btns.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(step_btns, text="Remove", width=90, command=self._remove_selected).pack(
            side="left"
        )
        ctk.CTkButton(step_btns, text="Clear", width=80, fg_color="#2A3140", command=self._clear_draft).pack(
            side="left", padx=(6, 0)
        )

        # Preview / detail
        right = ctk.CTkFrame(body, fg_color=_PANEL, corner_radius=8)
        right.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(right, text="Expansion preview", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        self.preview = ctk.CTkTextbox(right, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.preview.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.detail_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            right,
            textvariable=self.detail_var,
            text_color=_MUTED,
            wraplength=260,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 10))

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
            text="Refresh catalog",
            width=120,
            fg_color="#2A3140",
            command=self._reload_catalog,
        ).pack(side="right", padx=(0, 8))

    def _sync_title(self) -> None:
        self.draft.title = self.title_entry.get().strip() or "Untitled molecule"
        self._render_preview()

    def _reload_catalog(self) -> None:
        self.catalog = load_capability_catalog(self.project_root_path)
        self.refresh()
        self._emit("Capability catalog reloaded.", "ok")

    def refresh(self) -> None:
        library = load_library(self.automations_root)
        self._palette_items = build_palette(
            context=self.context,
            tabs=self.catalog.tabs,
            library=library,
        )
        tab = self.context.tab
        if tab:
            caps = self.catalog.tabs.get(tab)
            label = caps.label if caps else tab
            hot = f" [{caps.hotkey}]" if caps and caps.hotkey else ""
            self.context_var.set(f"Context: {label}{hot}")
        else:
            self.context_var.set("Context: (choose a tab)")
        self._render_palette()
        self._render_steps()
        self._render_preview()

    def _render_palette(self) -> None:
        for child in self.palette_list.winfo_children():
            child.destroy()
        self._selected_palette = None
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
            btn = ctk.CTkButton(
                self.palette_list,
                text=item.label,
                anchor="w",
                fg_color="#243041",
                hover_color="#314257",
                command=lambda idx=i: self._select_palette(idx),
            )
            btn.pack(fill="x", padx=4, pady=2)

    def _select_palette(self, index: int) -> None:
        self._selected_palette = index
        if 0 <= index < len(self._palette_items):
            item = self._palette_items[index]
            self.detail_var.set(item.detail)
            # Context-clear and tab selection apply immediately.
            if item.key == "ctx:clear_tab":
                self.context.clear()
                self.refresh()
                return
            if item.kind == "ensure_tab" and item.tab and self.context.tab is None:
                self._apply_palette_item(item)

    def _add_selected(self) -> None:
        if self._selected_palette is None:
            self._emit("Select a palette item first.", "warn")
            return
        item = self._palette_items[self._selected_palette]
        if item.key == "ctx:clear_tab":
            self.context.clear()
            self.refresh()
            return
        self._apply_palette_item(item)

    def _apply_palette_item(self, item: PaletteItem) -> None:
        if item.kind == "ensure_tab" and item.tab:
            # Enter context; also record the tab open as a draft step when drafting buys.
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
            self._emit(f"Context → {item.tab}. Tab upgrades unlocked.", "ok")
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
            self._emit(f"Added seek+buy: {item.label}", "ok")
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
            self._emit(f"Added molecule: {item.label}", "ok")
            return

    def _render_steps(self) -> None:
        for child in self.steps_list.winfo_children():
            child.destroy()
        self._selected_step = None
        if not self.draft.steps:
            ctk.CTkLabel(
                self.steps_list,
                text="Empty — pick a tab, then add upgrades.",
                text_color=_MUTED,
            ).pack(anchor="w", padx=6, pady=8)
            return
        for i, step in enumerate(self.draft.steps):
            prefix = {
                "ensure_tab": "TAB",
                "seek_and_buy": "BUY",
                "molecule_ref": "MOL",
            }.get(step.kind, step.kind)
            text = f"{i + 1}. [{prefix}] {step.label}"
            btn = ctk.CTkButton(
                self.steps_list,
                text=text,
                anchor="w",
                fg_color="#243041",
                hover_color="#314257",
                command=lambda idx=i: self._select_step(idx),
            )
            btn.pack(fill="x", padx=4, pady=2)

    def _select_step(self, index: int) -> None:
        self._selected_step = index
        if 0 <= index < len(self.draft.steps):
            step = self.draft.steps[index]
            detail = step.detail
            if step.guards:
                down = ", ".join(step.guards.too_far_down) or "—"
                up = ", ".join(step.guards.too_far_up) or "—"
                detail = f"{detail}\n\nToo far up: {up}\nToo far down: {down}"
            self.detail_var.set(detail)

    def _remove_selected(self) -> None:
        if self._selected_step is None:
            self._emit("Select a draft step to remove.", "warn")
            return
        self.draft.remove_at(self._selected_step)
        self.refresh()

    def _clear_draft(self) -> None:
        self.draft.clear_steps()
        self.draft.title = "Untitled molecule"
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, self.draft.title)
        self.context.clear()
        self.refresh()

    def _render_preview(self) -> None:
        lines = preview_expansion(self.draft, self.catalog)
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "\n".join(lines))

    def _save(self) -> None:
        self._sync_title()
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
        msg = (
            f"Saved molecule “{result.collection_id}” "
            f"({len(result.event_paths)} atom file(s)). Reload Loops to pick it up."
        )
        self._emit(msg, "ok")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "\n".join(result.preview_lines) + f"\n\n→ {result.collection_path.name}")
        if self.on_exported:
            try:
                self.on_exported(result.collection_id)
            except Exception:
                pass
        # Keep drafting; library now includes this molecule for the active tab.
        self.refresh()
