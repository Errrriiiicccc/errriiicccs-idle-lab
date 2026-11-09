"""Click-through Live Control Overlay — clicks = hotkeys; non-clicks = icons (hold D describes)."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass, field

from idle_lab.live_control.buy_detect import DetectedBuySlot
from idle_lab.live_control.playbook import LiveControlPlaybook
from idle_lab.models import Rect
from idle_lab import win32_api

_MARKER_R = 15
_FLING_MARKER_R = 16
_LABEL_PAD_X = 8
_LABEL_PAD_Y = 4
_ANCHOR_INSET = 6
_OBSTACLE_PAD = 8
_PATH_CROSS_PENALTY = 120.0
_PREF_MISS_PENALTY = 22.0

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
_CLAIM_OUTLINE = "#E090D0"
_CLAIM_FILL = "#201018"
_REFRESH_OUTLINE = "#E0B85E"
_REFRESH_FILL = "#201808"
_GLYPH = "#F2F6FA"

# Descriptor diagram layer (hold D)
_DIM_FILL = "#0A0C10"
_DESC_LINE = "#C8D4E0"
_DESC_BOX_OUTLINE = "#D8E2EC"
_DESC_BOX_FILL = "#1A222C"
_DESC_TEXT = "#F2F6FA"

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
    show_descriptors: bool = False
    paused: bool = False


@dataclass(frozen=True)
class _Box:
    left: float
    top: float
    right: float
    bottom: float

    def overlaps(self, other: _Box) -> bool:
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )

    def contains_point(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


@dataclass
class _DescribeLayout:
    """Diagram-style HV label placer: avoid obstacles, minimize Manhattan travel."""

    bounds: _Box
    obstacles: list[_Box] = field(default_factory=list)

    def add_circle(self, x: float, y: float, radius: float) -> None:
        r = radius + _OBSTACLE_PAD
        self.obstacles.append(_Box(x - r, y - r, x + r, y + r))

    def add_box(self, box: _Box) -> None:
        self.obstacles.append(box)

    def fits(self, box: _Box) -> bool:
        b = self.bounds
        if box.left < b.left or box.right > b.right or box.top < b.top or box.bottom > b.bottom:
            return False
        return not any(box.overlaps(obs) for obs in self.obstacles)

    def segment_hits(self, x0: float, y0: float, x1: float, y1: float) -> int:
        """Count obstacles a thin HV segment AABB collides with (endpoint marks excluded lightly)."""

        pad = 2.0
        seg = _Box(
            min(x0, x1) - pad,
            min(y0, y1) - pad,
            max(x0, x1) + pad,
            max(y0, y1) + pad,
        )
        return sum(1 for obs in self.obstacles if seg.overlaps(obs))

    def route_score(self, ax: float, ay: float, cx: float, cy: float) -> tuple[float, str]:
        """Pick H-then-V vs V-then-H; return (score, mode)."""

        manhattan = abs(cx - ax) + abs(cy - ay)
        hv_hits = self.segment_hits(ax, ay, cx, ay) + self.segment_hits(cx, ay, cx, cy)
        vh_hits = self.segment_hits(ax, ay, ax, cy) + self.segment_hits(ax, cy, cx, cy)
        hv = manhattan + hv_hits * _PATH_CROSS_PENALTY
        vh = manhattan + vh_hits * _PATH_CROSS_PENALTY
        if hv <= vh:
            return hv, "hv"
        return vh, "vh"

    def place(
        self,
        attach: tuple[float, float],
        half_w: float,
        half_h: float,
        *,
        prefer: str | None = None,
    ) -> tuple[float, float, str] | None:
        """Return (label_cx, label_cy, route_mode) for the cheapest free pocket."""

        ax, ay = attach
        # Preferred half-plane first (tabs want up even when a short down path exists).
        prefer_sets: list[list[float]] = []
        if prefer == "up":
            prefer_sets.append([90.0, 45.0, 135.0, 60.0, 120.0, 30.0, 150.0])
        elif prefer == "down":
            prefer_sets.append([270.0, 225.0, 315.0, 240.0, 300.0])
        elif prefer == "left":
            prefer_sets.append([180.0, 135.0, 225.0, 150.0, 210.0])
        elif prefer == "right":
            prefer_sets.append([0.0, 45.0, 315.0, 30.0, 330.0])
        prefer_sets.append([90.0, 0.0, 180.0, 270.0, 45.0, 135.0, 225.0, 315.0])
        distances = [d for d in range(28, 260, 8)]
        seen: set[tuple[int, int]] = set()
        for bearings in prefer_sets:
            best: tuple[float, float, float, str] | None = None
            for dist in distances:
                for deg in bearings:
                    rad = math.radians(deg)
                    # Screen Y grows downward — invert sin so 90° is up.
                    raw_x = ax + dist * math.cos(rad)
                    raw_y = ay - dist * math.sin(rad)
                    cx = min(max(raw_x, self.bounds.left + half_w), self.bounds.right - half_w)
                    cy = min(max(raw_y, self.bounds.top + half_h), self.bounds.bottom - half_h)
                    key = (int(round(cx)), int(round(cy)))
                    if key in seen:
                        continue
                    seen.add(key)
                    box = _Box(cx - half_w, cy - half_h, cx + half_w, cy + half_h)
                    if not self.fits(box):
                        continue
                    # Hard half-plane filter while still in the preferred pass.
                    if prefer == "up" and cy >= ay - 2:
                        continue
                    if prefer == "down" and cy <= ay + 2:
                        continue
                    if prefer == "left" and cx >= ax + 2:
                        continue
                    if prefer == "right" and cx <= ax - 2:
                        continue
                    score, mode = self.route_score(ax, ay, cx, cy)
                    if best is None or score < best[0]:
                        best = (score, cx, cy, mode)
            if best is not None:
                return best[1], best[2], best[3]
            # Fallback pass: drop the hard half-plane filter (prefer_sets last entry).
            prefer = None
        return None


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

    def _anchor_bounds(self) -> tuple[float, float, float, float]:
        """Canvas-space inset box for the anchored window."""

        assert self._anchor is not None and self._vs is not None
        left = self._anchor.left - self._vs.left + _ANCHOR_INSET
        top = self._anchor.top - self._vs.top + _ANCHOR_INSET
        right = self._anchor.right - self._vs.left - _ANCHOR_INSET
        bottom = self._anchor.bottom - self._vs.top - _ANCHOR_INSET
        return left, top, right, bottom

    def _paint(self) -> None:
        self.canvas.delete("all")
        pb = self._playbook
        anchor = self._anchor
        if pb is None or anchor is None or self._vs is None:
            return
        state = self._state
        paused = bool(state.paused)
        glyph = _PAUSED_GLYPH if paused else _GLYPH
        describe = bool(state.show_descriptors) and not paused
        show_keys = describe

        if describe:
            self._paint_dim()
            self._paint_descriptors(pb, state)

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

        stat = pb.stat_collect
        self._stat_badge(
            float(stat.get("nx") or 0.15),
            float(stat.get("ny") or 0.09),
            key=pb.hotkey_for("stat_collect") or "V",
            outline=_PAUSED_OUTLINE if paused else _STAT_OUTLINE,
            fill=_PAUSED_FILL if paused else _STAT_FILL,
            show_hotkeys=show_keys,
            glyph=glyph,
        )
        chrome = pb.chrome
        self._claim_badge(
            float(chrome.get("claim_badge_nx") or 0.20),
            float(chrome.get("claim_badge_ny") or 0.50),
            key=pb.hotkey_for("claim_gem") or "C",
            outline=_PAUSED_OUTLINE if paused else _CLAIM_OUTLINE,
            fill=_PAUSED_FILL if paused else _CLAIM_FILL,
            show_hotkeys=show_keys,
            glyph=glyph,
        )
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

    def _paint_dim(self) -> None:
        """Gray the anchored window under marks so HV descriptors read clearly."""

        left, top, right, bottom = self._anchor_bounds()
        # Stipple keeps the game faintly visible under a magenta-keyed canvas.
        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            outline="",
            fill=_DIM_FILL,
            stipple="gray50",
            tags="dim",
        )

    def _paint_descriptors(self, pb: LiveControlPlaybook, state: LiveControlOverlayState) -> None:
        left, top, right, bottom = self._anchor_bounds()
        layout = _DescribeLayout(bounds=_Box(left, top, right, bottom))

        # Reserve every mark first so labels pathfind around icons, not through them.
        for tab in pb.tabs.values():
            layout.add_circle(*self._to_canvas(tab.nx, tab.ny), _MARKER_R)
        buy_indexed: list[tuple[tuple[float, float], int]] = []
        scroll_pts: list[tuple[float, float]] = []
        if state.panel_open and state.tab:
            if state.live_slots:
                buy_indexed = [(self._to_canvas(s.nx, s.ny), int(s.index)) for s in state.live_slots]
            else:
                buy_indexed = [
                    (self._to_canvas(s.nx, s.ny), int(s.index)) for s in pb.buy_slots(state.tab)
                ]
            for pt, _idx in buy_indexed:
                layout.add_circle(*pt, _MARKER_R)
            scroll = pb.scroll
            scroll_pts = [
                self._to_canvas(
                    float(scroll.get("fling_up_badge_nx") or 0.94),
                    float(scroll.get("fling_up_badge_ny") or 0.615),
                ),
                self._to_canvas(
                    float(scroll.get("up_badge_nx") or 0.94),
                    float(scroll.get("up_badge_ny") or 0.655),
                ),
                self._to_canvas(
                    float(scroll.get("down_badge_nx") or 0.94),
                    float(scroll.get("down_badge_ny") or 0.830),
                ),
                self._to_canvas(
                    float(scroll.get("fling_down_badge_nx") or 0.94),
                    float(scroll.get("fling_down_badge_ny") or 0.870),
                ),
            ]
            for i, pt in enumerate(scroll_pts):
                layout.add_circle(*pt, _FLING_MARKER_R if i in (0, 3) else _MARKER_R)
        stat = pb.stat_collect
        stat_pt = self._to_canvas(float(stat.get("nx") or 0.15), float(stat.get("ny") or 0.09))
        layout.add_circle(*stat_pt, _MARKER_R)
        chrome = pb.chrome
        claim_pt = self._to_canvas(
            float(chrome.get("claim_badge_nx") or 0.20),
            float(chrome.get("claim_badge_ny") or 0.50),
        )
        layout.add_circle(*claim_pt, _MARKER_R)
        refresh_pt = self._to_canvas(
            float(chrome.get("refresh_badge_nx") or 0.92),
            float(chrome.get("refresh_badge_ny") or 0.50),
        )
        layout.add_circle(*refresh_pt, _MARKER_R)

        # Tight pockets first so later labels still have room.
        if buy_indexed:
            self._descriptor_buy(layout, buy_indexed, "Buy")
        if len(scroll_pts) >= 2:
            self._descriptor_column(layout, scroll_pts, "Scroll")
        tabs = list(pb.tabs.values())
        if len(tabs) >= 2:
            self._descriptor_tabs(layout, [self._to_canvas(t.nx, t.ny) for t in tabs], "Switch Upgrade Tabs")
        self._descriptor_singleton(layout, stat_pt, "Stat Collect", prefer="left")
        self._descriptor_singleton(layout, claim_pt, "Claim Diamonds", prefer="left")
        self._descriptor_singleton(layout, refresh_pt, "Refresh", prefer="right")

    def _descriptor_tabs(
        self,
        layout: _DescribeLayout,
        points: list[tuple[float, float]],
        label: str,
    ) -> None:
        """Horizontal spine; label pathfinds to the nearest free pocket (prefer up)."""

        if len(points) < 2:
            return
        ordered = sorted(points, key=lambda p: p[0])
        y = sum(p[1] for p in ordered) / len(ordered)
        x0, x1 = ordered[0][0], ordered[-1][0]
        self._line(x0, y, x1, y)
        attach = ((x0 + x1) / 2.0, y)
        self._place_routed_label(layout, attach, label, prefer="up")

    def _descriptor_column(
        self,
        layout: _DescribeLayout,
        points: list[tuple[float, float]],
        label: str,
    ) -> None:
        """Vertical spine; label pathfinds beside the column."""

        if len(points) < 2:
            return
        ordered = sorted(points, key=lambda p: p[1])
        x = sum(p[0] for p in ordered) / len(ordered)
        y0, y1 = ordered[0][1], ordered[-1][1]
        self._line(x, y0, x, y1)
        attach = (x, (y0 + y1) / 2.0)
        self._place_routed_label(layout, attach, label, prefer="left")

    def _descriptor_buy(
        self,
        layout: _DescribeLayout,
        indexed: list[tuple[tuple[float, float], int]],
        label: str,
    ) -> None:
        """Tree: cols 1-3-5 & 2-4-6 + bridge 3-4; label pathfinds into a free bay."""

        if not indexed:
            return
        by_index = {idx: pt for pt, idx in indexed}
        for col in ((1, 3, 5), (2, 4, 6)):
            pts = [by_index[i] for i in col if i in by_index]
            if len(pts) >= 2:
                ordered = sorted(pts, key=lambda p: p[1])
                x = sum(p[0] for p in ordered) / len(ordered)
                self._line(x, ordered[0][1], x, ordered[-1][1])
        if 3 in by_index and 4 in by_index:
            self._line(by_index[3][0], by_index[3][1], by_index[4][0], by_index[4][1])
            attach = (
                (by_index[3][0] + by_index[4][0]) / 2.0,
                (by_index[3][1] + by_index[4][1]) / 2.0,
            )
        else:
            xs = [p[0] for p, _ in indexed]
            ys = [p[1] for p, _ in indexed]
            attach = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
        self._place_routed_label(layout, attach, label, prefer="up")

    def _descriptor_singleton(
        self,
        layout: _DescribeLayout,
        point: tuple[float, float],
        label: str,
        *,
        prefer: str,
    ) -> None:
        """One mark → HV route → label in the nearest free pocket."""

        self._place_routed_label(layout, point, label, prefer=prefer)

    def _place_routed_label(
        self,
        layout: _DescribeLayout,
        attach: tuple[float, float],
        text: str,
        *,
        prefer: str | None = None,
    ) -> None:
        tw, th = self._measure_label(text)
        half_w = tw / 2.0 + _LABEL_PAD_X
        half_h = th / 2.0 + _LABEL_PAD_Y
        placed = layout.place(attach, half_w, half_h, prefer=prefer)
        ax, ay = attach
        if placed is None:
            # Last resort: clamp above/beside attach inside bounds (may still crowd).
            cx = min(max(ax, layout.bounds.left + half_w), layout.bounds.right - half_w)
            cy = min(max(ay - (_MARKER_R + half_h + 8), layout.bounds.top + half_h), layout.bounds.bottom - half_h)
            mode = "vh"
        else:
            cx, cy, mode = placed
        if mode == "hv":
            self._line(ax, ay, cx, ay)
            self._line(cx, ay, cx, cy)
        else:
            self._line(ax, ay, ax, cy)
            self._line(ax, cy, cx, cy)
        self._label_box_center(cx, cy, text, half_w=half_w, half_h=half_h)
        layout.add_box(_Box(cx - half_w, cy - half_h, cx + half_w, cy + half_h))

    def _line(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.canvas.create_line(x0, y0, x1, y1, fill=_DESC_LINE, width=2)

    def _measure_label(self, text: str) -> tuple[float, float]:
        font = ("Segoe UI", 10, "bold")
        probe = self.canvas.create_text(0, 0, text=text, font=font, anchor="nw")
        bbox = self.canvas.bbox(probe)
        self.canvas.delete(probe)
        if bbox is None:
            return 40.0, 14.0
        return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])

    def _label_box_center(
        self,
        cx: float,
        cy: float,
        text: str,
        *,
        half_w: float,
        half_h: float,
    ) -> None:
        font = ("Segoe UI", 10, "bold")
        self.canvas.create_rectangle(
            cx - half_w,
            cy - half_h,
            cx + half_w,
            cy + half_h,
            outline=_DESC_BOX_OUTLINE,
            fill=_DESC_BOX_FILL,
            width=1,
        )
        self.canvas.create_text(cx, cy, text=text, fill=_DESC_TEXT, font=font)

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
        """Non-click action: icon by default; hold D flips the mark to its hotkey."""

        x, y = self._to_canvas(nx, ny)
        r = radius
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
        mark = str(key) if show_hotkeys else icon
        font = ("Segoe UI", 11, "bold") if show_hotkeys else icon_font
        self.canvas.create_text(x, y, text=mark, fill=glyph, font=font)

    def _stat_badge(
        self,
        nx: float,
        ny: float,
        *,
        key: str,
        outline: str,
        fill: str,
        show_hotkeys: bool,
        glyph: str = _GLYPH,
    ) -> None:
        """Stat collect: clipboard/notepad glyph (or hotkey while holding D)."""

        x, y = self._to_canvas(nx, ny)
        r = _MARKER_R
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
        if show_hotkeys:
            self.canvas.create_text(x, y, text=str(key), fill=glyph, font=("Segoe UI", 11, "bold"))
            return
        # Clipboard body + clip tab.
        self.canvas.create_rectangle(x - 7, y - 5, x + 7, y + 8, outline=glyph, width=1.5)
        self.canvas.create_rectangle(x - 4, y - 9, x + 4, y - 3, outline=glyph, fill=fill, width=1.5)
        self.canvas.create_line(x - 4, y - 1, x + 4, y - 1, fill=glyph, width=1)
        self.canvas.create_line(x - 4, y + 2, x + 4, y + 2, fill=glyph, width=1)
        self.canvas.create_line(x - 4, y + 5, x + 2, y + 5, fill=glyph, width=1)

    def _claim_badge(
        self,
        nx: float,
        ny: float,
        *,
        key: str,
        outline: str,
        fill: str,
        show_hotkeys: bool,
        glyph: str = _GLYPH,
    ) -> None:
        """Timed gem CLAIM: diamond glyph (or hotkey while holding D)."""

        x, y = self._to_canvas(nx, ny)
        r = _MARKER_R
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=outline, fill=fill, width=2)
        if show_hotkeys:
            self.canvas.create_text(x, y, text=str(key), fill=glyph, font=("Segoe UI", 11, "bold"))
            return
        self.canvas.create_polygon(
            x,
            y - 8,
            x + 7,
            y,
            x,
            y + 8,
            x - 7,
            y,
            outline=glyph,
            fill="",
            width=1.5,
        )

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
        """Fling = stacked chevrons (or the hotkey letter while D is held)."""

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
