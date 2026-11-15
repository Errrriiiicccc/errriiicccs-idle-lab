"""Idle Lab expanded / condensed costume chrome (slice 1 skeleton)."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.feel_lab.themes import Look, default_look
from idle_lab.shell.skins import format_key_label
from idle_lab.shell.tabs import IDLE_LAB_TABS

POCKET_TOGGLE_LABEL = "F1"  # Settings-remappable later

# Stub expected-action maps per lab root (key, label) — pocket formats via skin.
POCKET_STUB_LEAVES: dict[str, tuple[tuple[str, str], ...]] = {
    "Info": (("1", "Jump to a Lab"), ("`", "Deactivate = Stop all")),
    "Live Overlay Lab": (("Enter", "Start live"), ("`", "Deactivate = Stop all")),
    "Molecule Lab": (
        ("A", "Atom area"),
        ("M", "Molecule area"),
        ("T", "Trial"),
        ("`", "Deactivate"),
    ),
    "Observation Lab": (
        ("U", "User capture"),
        ("A", "AI mission"),
        ("`", "Deactivate"),
    ),
}

# User-facing name is collapsed; keep CONDENSED_* alias for older imports.
COLLAPSED_OUTSIDE_CHORDS: tuple[tuple[str, str], ...] = (
    ("D", "Hold details (on glass)"),
    ("Esc", "Exit Live Overlay / Observation"),
    ("`", "Deactivate = Stop all"),
)
CONDENSED_OUTSIDE_CHORDS = COLLAPSED_OUTSIDE_CHORDS

ATOM_CREATE_POCKET_LEAVES: dict[str, tuple[tuple[str, str], ...]] = {
    "kind": (("1", "Automation"), ("2", "Phase map"), ("Esc", "Back to Atom Lab")),
    "create": (
        ("B", "Basic Gesture"),
        ("P", "Playbook"),
        ("E", "Edit"),
        ("Esc", "Save / leave"),
    ),
    "playbook": (("Esc", "Back to Create"),),
    "edit": (("W/S", "Select"), ("R/F", "Reorder"), ("Esc", "Back to Create")),
    "phase_map": (
        ("G", "Keys"),
        ("H", "Phases"),
        ("T", "Targets"),
        ("S", "Scroll"),
        ("Esc", "Save / leave"),
    ),
}


class HotkeyPocket(ctk.CTkFrame):
    """Docked hotkey flight deck at the bottom of the left rail."""

    def __init__(
        self,
        master,
        *,
        look: Look | None = None,
        on_toggle: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        self._look = look or default_look()
        super().__init__(master, corner_radius=8, fg_color=self._look.board, **kwargs)
        self._body_visible = True
        self._focus_lab = "Info"
        self._on_toggle = on_toggle

        self._title = ctk.CTkFrame(self, fg_color=self._look.panel, corner_radius=0)
        self._title.pack(fill="x")
        self._title_label = ctk.CTkLabel(
            self._title,
            text=f"Hotkey flight deck · {POCKET_TOGGLE_LABEL} open/close",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self._look.line,
        )
        self._title_label.pack(side="left", padx=8, pady=6, fill="x", expand=True)
        self._min_btn = ctk.CTkButton(
            self._title,
            text="—",
            width=32,
            height=24,
            fg_color=self._look.live_bg,
            hover_color=self._look.live_hover,
            text_color=self._look.live_text,
            border_width=1 if self._look.style == "type" else 0,
            border_color=self._look.live_border,
            command=on_toggle or self.toggle_body,
        )
        self._min_btn.pack(side="right", padx=6, pady=4)

        self._focus_label = ctk.CTkLabel(
            self,
            text="Focus: Info",
            anchor="w",
            text_color=self._look.esc_pop,
            font=ctk.CTkFont(size=11),
        )
        self._focus_label.pack(fill="x", padx=8, pady=(4, 0))

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self._leaf_labels: list[ctk.CTkLabel] = []
        self.set_focus_lab("Info")

    def apply_look(self, look: Look) -> None:
        self._look = look
        self.configure(fg_color=look.board)
        self._title.configure(fg_color=look.panel)
        self._title_label.configure(text_color=look.line)
        self._focus_label.configure(text_color=look.esc_pop)
        self._min_btn.configure(
            fg_color=look.live_bg,
            hover_color=look.live_hover,
            text_color=look.live_text,
            border_width=1 if look.style == "type" else 0,
            border_color=look.live_border,
        )
        self.set_focus_lab(self._focus_lab)

    def toggle_body(self) -> None:
        self._body_visible = not self._body_visible
        if self._body_visible:
            self._body.pack(fill="both", expand=True, padx=8, pady=(2, 8))
            self._min_btn.configure(text="—")
        else:
            self._body.pack_forget()
            self._min_btn.configure(text="+")

    def set_focus_lab(self, lab: str) -> None:
        name = lab if lab in IDLE_LAB_TABS else "Info"
        self._focus_lab = name
        leaves = POCKET_STUB_LEAVES.get(name, (("`", "Deactivate = Stop all"),))
        self.set_chords(f"Focus: {name}", leaves)

    def set_atom_create_phase(self, phase: str) -> None:
        key = str(phase or "create").strip().lower() or "create"
        leaves = ATOM_CREATE_POCKET_LEAVES.get(key) or ATOM_CREATE_POCKET_LEAVES["create"]
        self.set_chords(f"Focus: Atom Create · {key}", leaves)

    def set_chords(self, focus_line: str, leaves: tuple[tuple[str, str], ...]) -> None:
        self._focus_label.configure(text=focus_line)
        for widget in self._leaf_labels:
            try:
                widget.destroy()
            except Exception:
                pass
        self._leaf_labels.clear()
        for key, label in leaves:
            text = format_key_label(self._look, key, label)
            lbl = ctk.CTkLabel(
                self._body,
                text=text,
                anchor="w",
                text_color=self._look.caption,
                font=ctk.CTkFont(
                    size=max(11, self._look.font_size),
                    weight="bold" if self._look.bold_live else "normal",
                ),
            )
            lbl.pack(fill="x", pady=1)
            self._leaf_labels.append(lbl)


class LabTreeRail(ctk.CTkFrame):
    """Left-rail lab roots; one open path (sibling click collapses the other)."""

    def __init__(
        self,
        master,
        *,
        on_select: Callable[[str], None],
        look: Look | None = None,
        **kwargs,
    ) -> None:
        self._look = look or default_look()
        super().__init__(master, fg_color=self._look.board, width=220, **kwargs)
        self.pack_propagate(False)
        self._on_select = on_select
        self._selected = "Info"
        self._buttons: dict[str, ctk.CTkButton] = {}

        self._heading = ctk.CTkLabel(
            self,
            text="Labs",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self._look.muted,
        )
        self._heading.pack(fill="x", padx=10, pady=(10, 4))

        self._roots = ctk.CTkFrame(self, fg_color="transparent")
        self._roots.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        for name in IDLE_LAB_TABS:
            row = ctk.CTkFrame(self._roots, fg_color="transparent")
            row.pack(fill="x", pady=2)
            btn = ctk.CTkButton(
                row,
                text=name,
                anchor="w",
                height=self._look.btn_height + 4,
                fg_color="transparent",
                hover_color=self._look.live_hover,
                text_color=self._look.dorm_text,
                border_width=0,
                command=lambda n=name: self.select(n),
            )
            btn.pack(fill="x")
            self._buttons[name] = btn
        self._open_hint = ctk.CTkLabel(
            self._roots,
            text="",
            anchor="w",
            text_color=self._look.muted,
            font=ctk.CTkFont(size=11),
        )
        self._open_hint.pack(fill="x", padx=(12, 0), pady=(4, 0))
        self._paint()

    def apply_look(self, look: Look) -> None:
        self._look = look
        self.configure(fg_color=look.board)
        self._heading.configure(text_color=look.muted)
        self._open_hint.configure(text_color=look.muted)
        for btn in self._buttons.values():
            btn.configure(
                height=look.btn_height + 4,
                hover_color=look.live_hover,
            )
        self._paint()

    def select(self, name: str, *, notify: bool = True) -> None:
        if name not in IDLE_LAB_TABS:
            return
        self._selected = name
        self._paint()
        if notify:
            self._on_select(name)

    def _paint(self) -> None:
        look = self._look
        for name, btn in self._buttons.items():
            if name == self._selected:
                btn.configure(
                    fg_color=look.live_bg,
                    text_color=look.live_text,
                    border_width=1 if look.style == "type" else 0,
                    border_color=look.live_border,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=look.dorm_text,
                    border_width=0,
                )
        if self._open_hint is not None:
            self._open_hint.configure(text=f"Open path · {self._selected}")


def hide_tabview_segment(tabs: ctk.CTkTabview) -> None:
    """Drive tabs from the left rail; hide the built-in segmented control."""

    try:
        tabs._segmented_button.grid_remove()  # type: ignore[attr-defined]
    except Exception:
        try:
            tabs._segmented_button.pack_forget()  # type: ignore[attr-defined]
        except Exception:
            pass


def paint_collapsed_chords(parent, look: Look) -> list[ctk.CTkLabel]:
    labels: list[ctk.CTkLabel] = []
    for key, label in COLLAPSED_OUTSIDE_CHORDS:
        text = format_key_label(look, key, label)
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            anchor="w",
            text_color=look.caption,
            font=ctk.CTkFont(size=13, weight="bold" if look.bold_live else "normal"),
        )
        lbl.pack(fill="x", padx=12, pady=1)
        labels.append(lbl)
    return labels


paint_condensed_chords = paint_collapsed_chords
