"""Idle Lab expanded / condensed costume chrome (slice 1 skeleton)."""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from idle_lab.shell.tabs import IDLE_LAB_TABS

POCKET_TOGGLE_LABEL = "F1"  # Settings-remappable later

# Stub expected-action maps per lab root (pocket tracks focus; not live wiring yet).
POCKET_STUB_LEAVES: dict[str, tuple[str, ...]] = {
    "Info": ("[1] Jump to a Lab", "[`] Deactivate = Stop all"),
    "Live Overlay Lab": ("[Enter] Start live", "[`] Deactivate = Stop all"),
    "Molecule Lab": ("[A] Atom area", "[M] Molecule area", "[T] Trial", "[`] Deactivate"),
    "Observation Lab": ("[U] User capture", "[A] AI mission", "[`] Deactivate"),
}

CONDENSED_OUTSIDE_CHORDS = (
    "Hold D — details (on glass)",
    "Esc — exit Live Overlay / Observation",
    "` — Deactivate = Stop all",
)


class HotkeyPocket(ctk.CTkFrame):
    """Docked hotkey flight deck at the bottom of the left rail."""

    def __init__(
        self,
        master,
        *,
        on_toggle: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=8, fg_color="#1A1F28", **kwargs)
        self._body_visible = True
        self._focus_lab = "Info"

        title = ctk.CTkFrame(self, fg_color="#12161C", corner_radius=0)
        title.pack(fill="x")
        self._title_label = ctk.CTkLabel(
            title,
            text=f"Hotkey flight deck · {POCKET_TOGGLE_LABEL} open/close",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self._title_label.pack(side="left", padx=8, pady=6, fill="x", expand=True)
        self._min_btn = ctk.CTkButton(
            title,
            text="—",
            width=32,
            height=24,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=on_toggle or self.toggle_body,
        )
        self._min_btn.pack(side="right", padx=6, pady=4)

        self._focus_label = ctk.CTkLabel(
            self,
            text="Focus: Info",
            anchor="w",
            text_color="#8EE0C2",
            font=ctk.CTkFont(size=11),
        )
        self._focus_label.pack(fill="x", padx=8, pady=(4, 0))

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True, padx=8, pady=(2, 8))
        self._leaf_labels: list[ctk.CTkLabel] = []
        self.set_focus_lab("Info")

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
        self._focus_label.configure(text=f"Focus: {name}")
        for widget in self._leaf_labels:
            try:
                widget.destroy()
            except Exception:
                pass
        self._leaf_labels.clear()
        for line in POCKET_STUB_LEAVES.get(name, ("[`] Deactivate = Stop all",)):
            lbl = ctk.CTkLabel(
                self._body,
                text=line,
                anchor="w",
                text_color="#A8B4C4",
                font=ctk.CTkFont(size=12),
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
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="#141820", width=220, **kwargs)
        self.pack_propagate(False)
        self._on_select = on_select
        self._selected = "Info"
        self._buttons: dict[str, ctk.CTkButton] = {}
        self._open_hint: ctk.CTkLabel | None = None

        ctk.CTkLabel(
            self,
            text="Labs",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7E8796",
        ).pack(fill="x", padx=10, pady=(10, 4))

        self._roots = ctk.CTkFrame(self, fg_color="transparent")
        self._roots.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        for name in IDLE_LAB_TABS:
            row = ctk.CTkFrame(self._roots, fg_color="transparent")
            row.pack(fill="x", pady=2)
            btn = ctk.CTkButton(
                row,
                text=name,
                anchor="w",
                height=32,
                fg_color="transparent",
                hover_color="#2A3140",
                text_color="#D0D6E0",
                command=lambda n=name: self.select(n),
            )
            btn.pack(fill="x")
            self._buttons[name] = btn
        self._open_hint = ctk.CTkLabel(
            self._roots,
            text="",
            anchor="w",
            text_color="#7E8796",
            font=ctk.CTkFont(size=11),
        )
        self._open_hint.pack(fill="x", padx=(12, 0), pady=(4, 0))
        self._paint()

    def select(self, name: str, *, notify: bool = True) -> None:
        if name not in IDLE_LAB_TABS:
            return
        self._selected = name
        self._paint()
        if notify:
            self._on_select(name)

    def _paint(self) -> None:
        for name, btn in self._buttons.items():
            if name == self._selected:
                btn.configure(fg_color="#1E3A4A", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#D0D6E0")
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
