"""Click-through Live Control Overlay — clicks = hotkeys; non-clicks = icons (D reveals keys)."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from idle_lab.live_control.buy_detect import DetectedBuySlot
from idle_lab.live_control.playbook import LiveControlPlaybook
from idle_lab.models import Rect
from idle_lab import win32_api

_MARKER_R = 15
_FLING_MARKER_R = 16

# Live colors
_TAB_OUTLINE = "#6A90A8"
_TAB_ACTIVE_OUTLINE = "#7CF0B8"
_TAB_FILL = "#121820"
_TAB_ACTIVE_FILL = "#184838"
_BUY_ALIGNED = "#6AD0F0"
_BUY_AMBER = "#E0B85E"
_BUY_FILL = "#101820"
_SCROLL_OUTLINE = "#A0C0E0"
_SCROLL_FILL = "#121820"
_FLING_OUTLINE = "#C8E0FF"
_FLING_FILL = "#182028"
_STAT_OUTLINE = "#70E0A0"
_STAT_FILL = "#102018"
_REFRESH_OUTLINE = "#E0B85E"
_REFRESH_FILL = "#201808"
_GLYPH = "#F2F6FA"

# Paused: lose color, stay visible but inert.
_PAUSED_OUTLINE = "#4A5058"
_PAUSED_FILL = "#141618"
_PAUSED_GLYPH = "#7A8088"


@dataclass
class LiveControlOverlayState:
    panel_open: bool = False
    tab: str | None = None
    aligned: bool = True
    status: str = ""
    surface_ok: bool = True
    live_slots: tuple[DetectedBuySlot, ...] = ()
    show_hotkeys: bool = False
    paused: bool = False


class LiveControlOverlay:
    """Topmost click-through canvas: click targets show keys; non-clicks show icons."""

    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self._shown = False
        self._vs: Rect | None = None
        self._anchor: Rect | None = None
        self._playbook: LiveControlPlaybook | None = None
        self._state = LiveControlOverlayState()
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", "magenta")
        self.win.configure(bg="magenta")
        self.canvas = tk.Canvas(self.win, bg="magenta", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()
        self.win.update_idletasks()

    def destroy(self) -> None:
        try:
            self.win.destroy()
        except Exception:
            pass

    @property
    def shown(self) -> bool:
        return self._shown

    def hide(self) -> None:
        self.canvas.delete("all")
        if self._shown:
            self.win.withdraw()
            self._shown = False

    def show(self, playbook: LiveControlPlaybook, anchor: Rect, state: LiveControlOverlayState) -> None:
        self._playbook = playbook
        self._anchor = anchor
        self._state = state
        self._sync_geometry()
        if not self._shown:
            self.win.deiconify()
            self.win.update_idletasks()
            hwnd = win32_api.widget_hwnd(self.win)
            win32_api.add_exstyle(hwnd, win32_api.OVERLAY_EXSTYLE)
            win32_api.raise_topmost(hwnd)
            self._shown = True
        self._paint()

    def update(self, *, anchor: Rect | None = None, state: LiveControlOverlayState | None = None) -> None:
        if anchor is not None:
            self._anchor = anchor
        if state is not None:
            self._state = state
        if self._shown and self._playbook is not None and self._anchor is not None:
            self._sync_geometry()
            self._paint()

    def _sync_geometry(self) -> None:
        screen = win32_api.virtual_screen()
        if screen == self._vs:
            return
        self._vs = screen
        self.win.geometry(f"{screen.width}x{screen.height}+{screen.left}+{screen.top}")

    def _to_canvas(self, nx: float, ny: float) -> tuple[float, float]:
        assert self._anchor is not None and self._vs is not None
        x = self._anchor.left + nx * self._anchor.width - self._vs.left
        y = self._anchor.top + ny * self._anchor.height - self._vs.top
        return x, y

    def _paint(self) -> None:
        self.canvas.delete("all")
        pb = self._playbook
        anchor = self._anchor
        if pb is None or anchor is None or self._vs is None:
            return
        state = self._state
        paused = bool(state.paused)
        glyph = _PAUSED_GLYPH if paused else _GLYPH

        for tab in pb.tabs.values():
            key = pb.hotkey_for(f"tab_{tab.id}") or "?"
            active = state.panel_open and state.tab == tab.id
            if paused:
                outline, fill = _PAUSED_OUTLINE, _PAUSED_FILL
            else:
                outline = _TAB_ACTIVE_OUTLINE if active else _TAB_OUTLINE
                fill = _TAB_ACTIVE_FILL if active else _TAB_FILL
            self._key_circle(tab.nx, tab.ny, key, outline=outline, fill=fill, glyph=glyph)

        if state.panel_open and state.tab:
            if paused:
                buy_outline, buy_fill = _PAUSED_OUTLINE, _PAUSED_FILL
            else:
                buy_outline = _BUY_ALIGNED if state.aligned else _BUY_AMBER
                buy_fill = _BUY_FILL
            if state.live_slots:
                for slot in state.live_slots:
                    key = pb.hotkey_for(f"buy_{slot.index}") or str(slot.index)
                    self._key_circle(slot.nx, slot.ny, key, outline=buy_outline, fill=buy_fill, glyph=glyph)
            else:
                for slot in pb.buy_slots(state.tab):
                    key = pb.hotkey_for(f"buy_{slot.index}") or str(slot.index)
                    self._key_circle(slot.nx, slot.ny, key, outline=buy_outline, fill=buy_fill, glyph=glyph)
            scroll = pb.scroll
            show_keys = bool(state.show_hotkeys)
            scroll_outline = _PAUSED_OUTLINE if paused else _SCROLL_OUTLINE
            scroll_fill = _PAUSED_FILL if paused else _SCROLL_FILL
            self._action_badge(
                float(scroll.get("up_badge_nx") or 0.94),
                float(scroll.get("up_badge_ny") or 0.655),
                key=pb.hotkey_for("scroll_up") or "R",
                icon="▲",
                outline=scroll_outline,
                fill=scroll_fill,
                show_hotkeys=show_keys,
                glyph=glyph,
            )
            self._action_badge(
                float(scroll.get("down_badge_nx") or 0.94),
                float(scroll.get("down_badge_ny") or 0.830),
                key=pb.hotkey_for("scroll_down") or "F",
                icon="▼",
                outline=scroll_outline,
                fill=scroll_fill,
                show_hotkeys=show_keys,
                glyph=glyph,
            )
            self._scroll_fling_badge(
                float(scroll.get("fling_up_badge_nx") or 0.94),
                float(scroll.get("fling_up_badge_ny") or 0.615),
                key=pb.hotkey_for("fling_up") or "T",
                direction="up",
                show_hotkeys=show_keys,
                paused=paused,
                glyph=glyph,
            )
            self._scroll_fling_badge(
                float(scroll.get("fling_down_badge_nx") or 0.94),
                float(scroll.get("fling_down_badge_ny") or 0.870),
                key=pb.hotkey_for("fling_down") or "G",
                direction="down",
                show_hotkeys=show_keys,
                paused=paused,
                glyph=glyph,
            )

        show_keys = bool(state.show_hotkeys)
        stat = pb.stat_collect
        self._action_badge(
            float(stat.get("nx") or 0.15),
            float(stat.get("ny") or 0.09),
            key=pb.hotkey_for("stat_collect") or "V",
            icon="★",
            outline=_PAUSED_OUTLINE if paused else _STAT_OUTLINE,
            fill=_PAUSED_FILL if paused else _STAT_FILL,
            show_hotkeys=show_keys,
            glyph=glyph,
        )
        chrome = pb.chrome
        self._action_badge(
            float(chrome.get("refresh_badge_nx") or 0.92),
            float(chrome.get("refresh_badge_ny") or 0.50),
            key=pb.hotkey_for("refresh") or "B",
            icon="↻",
            outline=_PAUSED_OUTLINE if paused else _REFRESH_OUTLINE,
            fill=_PAUSED_FILL if paused else _REFRESH_FILL,
            show_hotkeys=show_keys,
            glyph=glyph,
            icon_font=("Segoe UI", 14, "bold"),
        )

    def _key_circle(
        self,
        nx: float,
        ny: float,
        key: str,
        *,
        outline: str,
        fill: str,
        glyph: str = _GLYPH,
        radius: int = _MARKER_R,
    ) -> None:
        x, y = self._to_canvas(nx, ny)
        r = radius
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
        self.canvas.create_text(x, y, text=str(key), fill=glyph, font=("Segoe UI", 11, "bold"))

    def _action_badge(
        self,
        nx: float,
        ny: float,
        *,
        key: str,
        icon: str,
        outline: str,
        fill: str,
        show_hotkeys: bool,
        glyph: str = _GLYPH,
        radius: int = _MARKER_R,
        icon_font: tuple[str, int, str] = ("Segoe UI", 12, "bold"),
    ) -> None:
        """Non-click action: icon by default; D flips the mark to its hotkey."""

        x, y = self._to_canvas(nx, ny)
        r = radius
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
        mark = str(key) if show_hotkeys else icon
        font = ("Segoe UI", 11, "bold") if show_hotkeys else icon_font
        self.canvas.create_text(x, y, text=mark, fill=glyph, font=font)

    def _scroll_fling_badge(
        self,
        nx: float,
        ny: float,
        *,
        key: str,
        direction: str,
        show_hotkeys: bool,
        paused: bool = False,
        glyph: str = _GLYPH,
    ) -> None:
        """Fling = stacked chevrons (or the hotkey letter when D has flipped the legend)."""

        x, y = self._to_canvas(nx, ny)
        r = _FLING_MARKER_R
        outline = _PAUSED_OUTLINE if paused else _FLING_OUTLINE
        fill = _PAUSED_FILL if paused else _FLING_FILL
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
        if show_hotkeys:
            self.canvas.create_text(x, y, text=str(key), fill=glyph, font=("Segoe UI", 11, "bold"))
            return
        chevron = "▲" if direction == "up" else "▼"
        font = ("Segoe UI", 9, "bold")
        gap = 7
        self.canvas.create_text(x, y - gap, text=chevron, fill=glyph, font=font)
        self.canvas.create_text(x, y, text=chevron, fill=glyph, font=font)
        self.canvas.create_text(x, y + gap, text=chevron, fill=glyph, font=font)
