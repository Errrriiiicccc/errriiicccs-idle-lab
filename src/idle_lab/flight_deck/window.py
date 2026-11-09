"""Movable topmost flight deck beside the anchored target."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from idle_lab.flight_deck.keymap import FlightDeckKeymap, KeymapNode
from idle_lab.flight_deck.keys import (
    BACK_TOKEN,
    DEFAULT_EXPAND_VK,
    DESCRIBE_TOKEN,
    display_menu_key,
    normalize_menu_key,
    vk_label,
)
from idle_lab.flight_deck.shell import (
    ShellPhase,
    inactive_prompt,
    live_control_active_prompt,
    live_control_legend_hint,
    molecule_lab_active_prompt,
    molecule_lab_legend_hint,
)
from idle_lab.models import Rect
from idle_lab import win32_api

_DECK_BG = "#141A22"
_ACCENT = "#9FD4F0"
_MUTED = "#7E8796"
_OK = "#8EE0C2"
_WARN = "#E7C36A"
_DANGER = "#F09595"

_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$")

_COLLAPSED_W = 280
_COLLAPSED_H = 56
_INACTIVE_H = 64
_ACTIVE_PROMPT_H = 92
_LIVE_CONTROL_H = 156
_QUIT_H = 78
_EXPANDED_W = 340
_EXPANDED_W_DETAIL = 420


def parse_geometry(value: str | None) -> tuple[int, int, int, int] | None:
    """Return (width, height, x, y) or None if unusable."""

    if not value:
        return None
    match = _GEOMETRY_RE.match(str(value).strip())
    if not match:
        return None
    width, height, x, y = (int(match.group(i)) for i in range(1, 5))
    if width < 80 or height < 36:
        return None
    # Withdrawn windows on Windows often report ±32000-style coords.
    if abs(x) > 30000 or abs(y) > 30000:
        return None
    return width, height, x, y


def clamp_geometry(width: int, height: int, x: int, y: int) -> str:
    """Keep the deck at least partly visible on the virtual desktop."""

    screen = win32_api.virtual_screen()
    width = max(200, min(int(width), max(screen.width, 200)))
    height = max(48, min(int(height), max(screen.height, 48)))
    min_visible = 40
    x = int(x)
    y = int(y)
    if x + width < screen.left + min_visible:
        x = screen.left
    if x > screen.right - min_visible:
        x = screen.right - width
    if y + height < screen.top + min_visible:
        y = screen.top
    if y > screen.bottom - min_visible:
        y = screen.bottom - height
    x = max(screen.left, min(x, screen.right - min_visible))
    y = max(screen.top, min(y, screen.bottom - min_visible))
    return f"{width}x{height}+{x}+{y}"


def sanitize_geometry(value: str | None) -> str | None:
    parsed = parse_geometry(value)
    if parsed is None:
        return None
    return clamp_geometry(*parsed)


class FlightDeckWindow(ctk.CTkToplevel):
    """Sparse in-flight HUD. Lab owns when it is shown; this window only renders."""

    # CTk's Windows dark-titlebar path withdraw()s the window; resizable()
    # schedules another pass ~10ms later. That races deck-first boot and Lab
    # open (Lab's own titlebar update() flushes the deferred withdraw), so the
    # deck vanishes. Prefer a mapped deck over a themed titlebar.
    _deactivate_windows_window_header_manipulation = True

    def __init__(
        self,
        master: Any,
        *,
        on_close: Callable[[], None],
        on_activate_toggle: Callable[[], None],
        on_pause: Callable[[], None],
        on_stop: Callable[[], None],
        on_geometry: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.title("Idle Lab · Flight deck")
        self.configure(fg_color=_DECK_BG)
        self.attributes("-topmost", True)
        self.resizable(True, True)
        self.minsize(200, 48)
        self.protocol("WM_DELETE_WINDOW", on_close)

        self._on_close = on_close
        self._on_activate_toggle = on_activate_toggle
        self._on_pause = on_pause
        self._on_stop = on_stop
        self._on_geometry = on_geometry
        self._expanded = False
        self._anchored = False
        self._running = False
        self._paused = False
        self._status_text = ""
        self._prompt_text = ""
        self._shell_phase = ShellPhase.INACTIVE
        self._lab_visible = True
        self._show_descriptions = False
        self._live_control_active = False
        self._lco_show_descriptors = False
        self._lco_paused = False
        self._molecule_lab_active = False
        self._molecule_lab_close_confirm = False
        self._expand_vk = DEFAULT_EXPAND_VK
        self._keymap: FlightDeckKeymap | None = None
        # Accordion: which top-level menu letter is open (None = all collapsed).
        self._open_menu_key: str | None = None
        self._placed_once = False
        self._geometry_job: str | None = None
        self._collapsed_pos: tuple[int, int] | None = None

        self._build()
        self.bind("<Configure>", self._on_configure)
        self.withdraw()
        # Break Win32 owner link to Lab so showing Lab does not unmap this deck.
        self.after(0, self._orphan_from_owner)

    def _build(self) -> None:
        self._pad = ctk.CTkFrame(self, fg_color="transparent")
        self._pad.pack(fill="both", expand=True, padx=8, pady=6)

        self.header = ctk.CTkFrame(self._pad, fg_color="transparent")
        self.header.pack(fill="x")

        self.close_button = ctk.CTkButton(
            self.header,
            text="Close [Esc]",
            width=92,
            height=26,
            fg_color="#2A3140",
            hover_color="#3A4558",
            command=self._on_close,
        )
        self.close_button.pack(side="left")

        self.activate_button = ctk.CTkButton(
            self.header,
            text="Activate Flight Deck [`]",
            width=168,
            height=26,
            fg_color="#1E3A4A",
            hover_color="#2A5568",
            text_color=_ACCENT,
            command=self._on_activate_toggle,
        )
        self.activate_button.pack(side="left", padx=(6, 0))
        # Alias kept for any older references during the rename.
        self.expand_button = self.activate_button

        self.pause_button = ctk.CTkButton(
            self.header,
            text="Pause (F7)",
            width=88,
            height=26,
            fg_color="#3A3520",
            hover_color="#5A4E28",
            text_color=_WARN,
            command=self._on_pause,
        )
        self.stop_button = ctk.CTkButton(
            self.header,
            text="Stop (F8)",
            width=88,
            height=26,
            fg_color="#5A3030",
            hover_color="#7A4040",
            text_color=_DANGER,
            command=self._on_stop,
        )

        self.run_label = ctk.CTkLabel(
            self._pad,
            text="",
            anchor="w",
            justify="left",
            text_color=_MUTED,
            font=ctk.CTkFont(size=11),
        )

        self.menu_frame = ctk.CTkFrame(self._pad, fg_color="#0E1319", corner_radius=8)
        self.menu_path = ctk.CTkLabel(
            self.menu_frame,
            text="",
            anchor="w",
            text_color=_ACCENT,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.menu_path.pack(fill="x", padx=10, pady=(8, 4))
        self.menu_list = ctk.CTkLabel(
            self.menu_frame,
            text="",
            anchor="nw",
            justify="left",
            text_color="#DCE4EE",
            font=ctk.CTkFont(size=12),
        )
        self.menu_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def set_expand_vk(self, vk: int) -> None:
        self._expand_vk = int(vk)
        self._sync_activate_button_label()

    @property
    def shell_phase(self) -> ShellPhase:
        return self._shell_phase

    @property
    def anchored(self) -> bool:
        return self._anchored

    def set_shell_phase(
        self,
        phase: ShellPhase | str,
        *,
        prompt: str = "",
        lab_visible: bool | None = None,
        anchored: bool | None = None,
    ) -> None:
        self._shell_phase = phase if isinstance(phase, ShellPhase) else ShellPhase(str(phase))
        if prompt or self._shell_phase in {ShellPhase.INACTIVE, ShellPhase.ACTIVE, ShellPhase.CLOSE_CONFIRM}:
            self._prompt_text = prompt or self._prompt_text
        if lab_visible is not None:
            self._lab_visible = bool(lab_visible)
        if anchored is not None:
            self._anchored = bool(anchored)
        if self._shell_phase is ShellPhase.INACTIVE:
            self._expanded = False
            self._open_menu_key = None
            self._show_descriptions = False
        elif self._shell_phase is ShellPhase.ACTIVE and self._anchored:
            self._expanded = True
        elif self._shell_phase is ShellPhase.ACTIVE:
            self._expanded = False
            self._open_menu_key = None
            self._show_descriptions = False
        elif self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self._expanded = False
            self._open_menu_key = None
            self._show_descriptions = False
        self._render_chrome()

    def set_lab_visible(self, visible: bool) -> None:
        self._lab_visible = bool(visible)
        self._render_chrome()

    def set_anchored(self, anchored: bool) -> None:
        self._anchored = bool(anchored)
        if self._shell_phase is ShellPhase.ACTIVE and self._anchored:
            self._expanded = True
        elif self._shell_phase is ShellPhase.ACTIVE:
            self._expanded = False
            self._open_menu_key = None
        self._render_chrome()

    def _sync_activate_button_label(self) -> None:
        key = vk_label(self._expand_vk)
        if self._live_control_active or self._molecule_lab_active:
            self.activate_button.configure(
                text=f"Deactivate [{key}]",
                state="disabled",
            )
        elif self._shell_phase is ShellPhase.INACTIVE:
            self.activate_button.configure(
                text=f"Activate Flight Deck [{key}]",
                state="normal",
            )
        else:
            self.activate_button.configure(
                text=f"Deactivate [{key}]",
                state="normal",
            )

    def _sync_close_button_label(self) -> None:
        if self._molecule_lab_close_confirm:
            self.close_button.configure(text="Stay [Esc]")
        elif self._molecule_lab_active:
            self.close_button.configure(text="Close Lab [Esc]")
        elif self._live_control_active:
            self.close_button.configure(text="Exit LCO [Esc]")
        elif self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            self.close_button.configure(text="Stay [Esc]")
        elif self._expanded and self._open_menu_key:
            self.close_button.configure(text="Back [Esc]")
        elif self._expanded and self._anchored:
            self.close_button.configure(text="Close [Esc]")
        else:
            self.close_button.configure(text="Close [Esc]")

    def set_molecule_lab_active(self, active: bool, *, close_confirm: bool = False) -> None:
        """Swap accordion for Molecule Lab Esc/Enter chrome."""

        self._molecule_lab_active = bool(active)
        self._molecule_lab_close_confirm = bool(active and close_confirm)
        if self._molecule_lab_active:
            self._open_menu_key = None
        else:
            self._molecule_lab_close_confirm = False
        self._render_chrome()

    def set_live_control_active(self, active: bool) -> None:
        """Swap accordion for the LCO status surface while overlay owns keys."""

        was = self._live_control_active
        self._live_control_active = bool(active)
        if self._live_control_active and not was:
            # Leave the U section when returning — Esc already means exit LCO.
            self._open_menu_key = None
            self._show_descriptions = False
            self._lco_show_descriptors = False
            self._lco_paused = False
        if not self._live_control_active:
            self._lco_show_descriptors = False
            self._lco_paused = False
        self._render_chrome()

    def set_live_control_legend(self, show_descriptors: bool) -> None:
        """Update the bold D hint while LCO hold-describe is active."""

        self._lco_show_descriptors = bool(show_descriptors)
        if self._live_control_active:
            self._render_menu()
            self._fit_live_control_size()

    def set_live_control_paused(self, paused: bool) -> None:
        """Gray-out pause: ` toggles; Esc still exits the whole LCO session."""

        self._lco_paused = bool(paused)
        if self._live_control_active:
            self._render_menu()
            self._fit_live_control_size()

    def set_keymap(self, keymap: FlightDeckKeymap | None) -> None:
        self._keymap = keymap
        if keymap is None or self._open_menu_key is None:
            self._open_menu_key = None
        elif self._keymap.child_for_key(self._keymap.roots, self._open_menu_key) is None:
            self._open_menu_key = None
        self._render_menu()

    def set_run_state(self, *, running: bool, paused: bool, status: str) -> None:
        self._running = bool(running)
        self._paused = bool(paused)
        self._status_text = status or ""
        # Do not auto-collapse the hotkey menu when a run starts.
        self._render_chrome()

    def set_expanded(self, expanded: bool) -> None:
        if self._shell_phase is not ShellPhase.ACTIVE or not self._anchored:
            return
        self._expanded = bool(expanded)
        if not self._expanded:
            self._open_menu_key = None
            self._show_descriptions = False
        self._render_chrome()

    def toggle_descriptions(self) -> bool:
        """D — show/hide chord descriptions. Returns True if handled."""

        if not self._expanded:
            return False
        self._show_descriptions = not self._show_descriptions
        self._render_menu()
        self._fit_expanded_size()
        return True

    @property
    def expanded(self) -> bool:
        return self._expanded

    @property
    def open_menu_key(self) -> str | None:
        return self._open_menu_key

    def open_menu_node(self) -> KeymapNode | None:
        if self._keymap is None or not self._open_menu_key:
            return None
        return self._keymap.child_for_key(self._keymap.roots, self._open_menu_key)

    def current_nodes(self) -> list[KeymapNode]:
        """Leaves under the open accordion section (empty if none open)."""

        node = self.open_menu_node()
        return list(node.children) if node is not None else []

    def go_back(self) -> bool:
        """X: collapse open section, or collapse the whole menu if none open."""

        if not self._expanded:
            return False
        if self._open_menu_key:
            self._open_menu_key = None
            self._render_menu()
            self._fit_expanded_size()
            return True
        self.collapse_menu()
        return True

    def navigate(self, token: str) -> dict[str, Any] | None:
        """Accordion: letter toggles a top menu; digit fires a leaf under the open menu.

        Returns a leaf action dict when a command is chosen. Menu stays expanded.
        """

        if self._molecule_lab_active:
            return None
        if self._live_control_active:
            return None
        if not self._expanded or self._keymap is None:
            return None
        norm = normalize_menu_key(token)
        if norm == normalize_menu_key(BACK_TOKEN):
            self.go_back()
            return None
        if norm == normalize_menu_key(DESCRIBE_TOKEN):
            self.toggle_descriptions()
            return None

        # Letter → open/close that top-level menu (only one open at a time).
        root = self._keymap.child_for_key(self._keymap.roots, token)
        if root is not None and not root.is_leaf:
            root_key = normalize_menu_key(root.key)
            if self._open_menu_key and normalize_menu_key(self._open_menu_key) == root_key:
                self._open_menu_key = None
            else:
                self._open_menu_key = root.key
            self._render_menu()
            self._fit_expanded_size()
            return None

        # Digit → leaf under the currently open menu.
        open_node = self.open_menu_node()
        if open_node is None:
            return None
        leaf = self._keymap.child_for_key(open_node.children, token)
        if leaf is None or not leaf.is_leaf:
            return None
        action = dict(leaf.action or {})
        action["_label"] = leaf.label
        action["_path"] = f"{open_node.label} › {leaf.label}"
        self._render_menu()
        return action

    def collapse_menu(self) -> None:
        self._expanded = False
        self._open_menu_key = None
        self._show_descriptions = False
        self._render_chrome()

    def show_deck(self, *, beside: Rect | None = None, geometry: str | None = None) -> None:
        placed = sanitize_geometry(geometry)
        if placed:
            try:
                # Prefer saved x/y; force collapsed height until expand.
                parsed = parse_geometry(placed)
                if parsed:
                    _w, _h, x, y = parsed
                    self.geometry(clamp_geometry(_COLLAPSED_W, _COLLAPSED_H, x, y))
                    self._collapsed_pos = (x, y)
                else:
                    self.geometry(placed)
                self._placed_once = True
            except Exception:
                placed = None
        if not placed and beside is not None:
            self._place_beside(beside)
            self._placed_once = True
        elif not placed and not self._placed_once:
            screen = win32_api.virtual_screen()
            self.geometry(clamp_geometry(_COLLAPSED_W, _COLLAPSED_H, screen.left + 40, screen.top + 80))
            self._placed_once = True
        self.ensure_onscreen()
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass
        self._orphan_from_owner()
        self._render_chrome()

    def hide_deck(self) -> None:
        self.collapse_menu()
        self.withdraw()

    def focus_deck(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _orphan_from_owner(self) -> None:
        """Detach from Lab's Win32 owner so Lab show/lift cannot unmap this deck."""

        try:
            self.update_idletasks()
            hwnd = win32_api.widget_hwnd(self)
            win32_api.clear_window_owner(hwnd)
        except Exception:
            pass

    def current_geometry(self) -> str:
        return self.geometry()

    def ensure_onscreen(self) -> None:
        sanitized = sanitize_geometry(self.geometry())
        if sanitized and sanitized != self.geometry():
            try:
                self.geometry(sanitized)
            except Exception:
                pass

    def _place_beside(self, rect: Rect) -> None:
        width, height = _COLLAPSED_W, _COLLAPSED_H
        screen = win32_api.virtual_screen()
        candidates = (
            (int(rect.right) + 12, int(rect.top)),
            (int(rect.left) - width - 12, int(rect.top)),
            (int(rect.left) + 24, int(rect.top) + 24),
            (screen.left + 40, screen.top + 80),
        )
        for x, y in candidates:
            geo = clamp_geometry(width, height, x, y)
            parsed = parse_geometry(geo)
            if parsed is None:
                continue
            _w, _h, px, py = parsed
            if px >= screen.left - 8 and py >= screen.top - 8:
                self.geometry(geo)
                self._collapsed_pos = (px, py)
                return
        geo = clamp_geometry(width, height, screen.left + 40, screen.top + 80)
        self.geometry(geo)
        parsed = parse_geometry(geo)
        if parsed:
            self._collapsed_pos = (parsed[2], parsed[3])

    def _xy(self) -> tuple[int, int]:
        try:
            return int(self.winfo_x()), int(self.winfo_y())
        except Exception:
            if self._collapsed_pos:
                return self._collapsed_pos
            screen = win32_api.virtual_screen()
            return screen.left + 40, screen.top + 80

    def _fit_collapsed_size(self) -> None:
        x, y = self._xy()
        self._collapsed_pos = (x, y)
        height = _COLLAPSED_H
        if self._shell_phase is ShellPhase.INACTIVE:
            height = _INACTIVE_H
        elif self._shell_phase is ShellPhase.ACTIVE and not self._anchored:
            height = _ACTIVE_PROMPT_H
        elif self._shell_phase is ShellPhase.CLOSE_CONFIRM:
            height = _QUIT_H
        try:
            self.geometry(clamp_geometry(_COLLAPSED_W, height, x, y))
        except Exception:
            pass

    def _fit_expanded_size(self) -> None:
        if self._live_control_active or self._molecule_lab_active:
            self._fit_live_control_size()
            return
        x, y = self._xy()
        roots = self._keymap.roots if self._keymap else []
        open_children = len(self.current_nodes())
        # All root rows + open children + X/D hints.
        base_rows = len(roots) + open_children + 3
        if self._show_descriptions:
            lines = 2 + base_rows * 2 + open_children
            width = _EXPANDED_W_DETAIL
            line_px = 16
        else:
            lines = 2 + base_rows
            width = _EXPANDED_W
            line_px = 18
        height = 56 + 36 + max(lines, 1) * line_px + 24
        height = max(200, min(height, 560))
        try:
            self.geometry(clamp_geometry(width, height, x, y))
        except Exception:
            pass

    def _fit_live_control_size(self) -> None:
        x, y = self._xy()
        try:
            self.geometry(clamp_geometry(_EXPANDED_W, _LIVE_CONTROL_H, x, y))
        except Exception:
            pass

    def _on_configure(self, _event=None) -> None:
        if self._on_geometry is None or not self.winfo_viewable():
            return
        if self._geometry_job is not None:
            try:
                self.after_cancel(self._geometry_job)
            except Exception:
                pass

        def save() -> None:
            self._geometry_job = None
            if self._on_geometry is None or not self.winfo_viewable():
                return
            # Persist position; prefer collapsed footprint so reopen stays compact.
            x, y = self._xy()
            sanitized = sanitize_geometry(clamp_geometry(_COLLAPSED_W, _COLLAPSED_H, x, y))
            if sanitized:
                self._on_geometry(sanitized)

        self._geometry_job = self.after(400, save)

    def _render_chrome(self) -> None:
        shell = self._shell_phase
        self._sync_close_button_label()
        self._sync_activate_button_label()

        if shell is ShellPhase.INACTIVE:
            self.pause_button.pack_forget()
            self.stop_button.pack_forget()
            if self.close_button.winfo_ismapped():
                self.close_button.pack_forget()
            if self.menu_frame.winfo_ismapped():
                self.menu_frame.pack_forget()
            if not self.activate_button.winfo_ismapped():
                self.activate_button.pack(side="left", padx=(0, 0))
            key = vk_label(self._expand_vk)
            prompt = self._prompt_text.strip() or inactive_prompt(activate_key=key)
            self.run_label.configure(text=prompt, text_color=_ACCENT)
            if not self.run_label.winfo_ismapped():
                self.run_label.pack(fill="x", pady=(4, 0))
            self._fit_collapsed_size()
            return

        if shell is ShellPhase.CLOSE_CONFIRM:
            self.pause_button.pack_forget()
            self.stop_button.pack_forget()
            if self.activate_button.winfo_ismapped():
                self.activate_button.pack_forget()
            if self.menu_frame.winfo_ismapped():
                self.menu_frame.pack_forget()
            if not self.close_button.winfo_ismapped():
                self.close_button.pack(side="left")
            prompt = self._prompt_text.strip() or (
                "Close flight deck? Enter = yes · Esc = stay"
                if self._lab_visible
                else "Quit Idle Lab? Enter = quit · Esc = stay"
            )
            self.run_label.configure(text=prompt, text_color=_DANGER)
            if not self.run_label.winfo_ismapped():
                self.run_label.pack(fill="x", pady=(4, 0))
            self._fit_collapsed_size()
            return

        # ACTIVE
        if not self.close_button.winfo_ismapped():
            self.close_button.pack(side="left")
        if not self.activate_button.winfo_ismapped():
            self.activate_button.pack(side="left", padx=(6, 0))

        if self._running:
            self.pause_button.pack(side="left", padx=(6, 0))
            self.stop_button.pack(side="left", padx=(6, 0))
            self.pause_button.configure(text="Resume (F7)" if self._paused else "Pause (F7)")
        else:
            self.pause_button.pack_forget()
            self.stop_button.pack_forget()

        if self._anchored and self._expanded:
            if self._live_control_active or self._molecule_lab_active:
                self.run_label.configure(text="", text_color=_MUTED)
                if self.run_label.winfo_ismapped():
                    self.run_label.pack_forget()
                if not self.menu_frame.winfo_ismapped():
                    self.menu_frame.pack(fill="both", expand=True, pady=(6, 0))
                self._render_menu()
                self._fit_live_control_size()
                return
            if self._running and self._status_text:
                color = _WARN if self._paused else _OK
                self.run_label.configure(text=self._status_text, text_color=color)
            elif not self._lab_visible:
                self.run_label.configure(text="I = open Lab · R = restart", text_color=_MUTED)
            else:
                self.run_label.configure(text="R = restart", text_color=_MUTED)
            if not self.run_label.winfo_ismapped():
                self.run_label.pack(fill="x", pady=(4, 0))
            if not self.menu_frame.winfo_ismapped():
                self.menu_frame.pack(fill="both", expand=True, pady=(6, 0))
            self._render_menu()
            self._fit_expanded_size()
            return

        # Active, not anchored (or menu collapsed): prompt for A / I / Enter.
        if self.menu_frame.winfo_ismapped():
            self.menu_frame.pack_forget()
        prompt = self._prompt_text.strip() or "A = set anchor"
        self.run_label.configure(text=prompt, text_color=_ACCENT)
        if not self.run_label.winfo_ismapped():
            self.run_label.pack(fill="x", pady=(4, 0))
        self._fit_collapsed_size()

    def _render_menu(self) -> None:
        if self._molecule_lab_active:
            hint_color = _WARN if self._molecule_lab_close_confirm else _ACCENT
            self.menu_path.configure(
                text=molecule_lab_legend_hint(close_confirm=self._molecule_lab_close_confirm),
                text_color=hint_color,
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            self.menu_list.configure(
                text=molecule_lab_active_prompt(close_confirm=self._molecule_lab_close_confirm)
            )
            self._sync_close_button_label()
            return
        if self._live_control_active:
            hint_color = _MUTED if self._lco_paused else _WARN
            self.menu_path.configure(
                text=live_control_legend_hint(
                    show_descriptors=self._lco_show_descriptors,
                    paused=self._lco_paused,
                ),
                text_color=hint_color,
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            self.menu_list.configure(text=live_control_active_prompt(paused=self._lco_paused))
            self._sync_close_button_label()
            return
        # Restore path styling when leaving the LCO / Lab surface.
        self.menu_path.configure(text_color=_ACCENT, font=ctk.CTkFont(size=12, weight="bold"))
        if self._keymap is None:
            self.menu_path.configure(text="No flight catalog loaded")
            self.menu_list.configure(text="")
            return
        open_node = self.open_menu_node()
        if open_node is not None:
            self.menu_path.configure(text=f"{open_node.label}  ·  letter → menu, digit → run")
        else:
            self.menu_path.configure(text="Hotkeys  ·  letter opens a menu")
        lines: list[str] = []
        open_norm = normalize_menu_key(self._open_menu_key or "")
        for root in self._keymap.roots:
            key = display_menu_key(root.key)
            is_open = normalize_menu_key(root.key) == open_norm
            marker = "▼" if is_open else "▷"
            lines.append(f"  {key:<4} {marker} {root.label}")
            if self._show_descriptions and not is_open:
                detail = (root.description or "").strip()
                if detail:
                    lines.append(f"         {detail}")
            if not is_open:
                continue
            for child in root.children:
                ckey = display_menu_key(child.key)
                lines.append(f"       {ckey:<4} {child.label}")
                if self._show_descriptions:
                    detail = (child.description or "").strip() or "(no description)"
                    lines.append(f"            {detail}")
        if open_node is not None:
            lines.append(f"  {BACK_TOKEN:<4} Collapse {open_node.label}")
        else:
            lines.append(f"  {BACK_TOKEN:<4} Collapse menu")
        desc_state = "on — press D to hide" if self._show_descriptions else "press D to show"
        lines.append(f"  {DESCRIBE_TOKEN:<4} Descriptions ({desc_state})")
        self.menu_list.configure(text="\n".join(lines) if lines else "  (empty)")
        self._sync_close_button_label()
