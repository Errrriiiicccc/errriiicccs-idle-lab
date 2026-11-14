"""Atom Create visual layer — queue panel + click/drag/OCR glyphs on the anchor."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any, Literal

from idle_lab.models import Rect
from idle_lab.shared_overlay.primitives import (
    CURRENT_FILL,
    CURRENT_OUTLINE,
    QUEUED_FILL,
    QUEUED_OUTLINE,
)
from idle_lab.shell.atom_create import step_detail_lines, step_label
from idle_lab.shell.atom_phase_map import (
    format_phase_tree_lines,
    queue_piece_line,
    role_glyph,
)
from idle_lab import win32_api

_MARKER = 30
_QUEUE_W = 300
_QUEUE_H = 320
_QUEUE_H_PHASE = 420
_GHOST = 36

PlaceKind = Literal["click", "drag_start", "drag_end"]


class _ClickMark(tk.Toplevel):
    """Small numbered circle that receives mouse (not click-through)."""

    def __init__(
        self,
        root: tk.Misc,
        index: int,
        *,
        on_moved: Callable[[int, int, int], None],
        on_released: Callable[[int, int, int], None],
        label: str | None = None,
    ) -> None:
        super().__init__(root)
        self.index = index
        self._on_moved = on_moved
        self._on_released = on_released
        self.dragging = False
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "magenta")
        self.configure(bg="magenta")
        self.canvas = tk.Canvas(
            self,
            width=_MARKER,
            height=_MARKER,
            bg="magenta",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self._oval = self.canvas.create_oval(
            2, 2, _MARKER - 2, _MARKER - 2, fill=QUEUED_FILL, outline=QUEUED_OUTLINE, width=2
        )
        self._text = self.canvas.create_text(
            _MARKER // 2,
            _MARKER // 2,
            text=label or str(index + 1),
            fill="white",
            font=("Segoe UI", 9, "bold"),
        )
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.withdraw()

    def set_selected(self, selected: bool) -> None:
        outline = CURRENT_OUTLINE if selected else QUEUED_OUTLINE
        fill = CURRENT_FILL if selected else QUEUED_FILL
        self.canvas.itemconfigure(self._oval, outline=outline, fill=fill)

    def set_index_label(self, index: int, *, text: str | None = None) -> None:
        self.index = index
        self.canvas.itemconfigure(self._text, text=text or str(index + 1))

    def show_at(self, screen_x: int, screen_y: int) -> None:
        if self.dragging:
            return
        left = int(screen_x) - _MARKER // 2
        top = int(screen_y) - _MARKER // 2
        self.geometry(f"{_MARKER}x{_MARKER}+{left}+{top}")
        if not self.winfo_viewable():
            self.deiconify()
            self.lift()

    def _press(self, _event) -> None:
        self.dragging = True

    def _drag(self, event) -> None:
        self.dragging = True
        left = int(event.x_root) - _MARKER // 2
        top = int(event.y_root) - _MARKER // 2
        self.geometry(f"{_MARKER}x{_MARKER}+{left}+{top}")
        self._on_moved(self.index, int(event.x_root), int(event.y_root))

    def _release(self, event) -> None:
        self.dragging = False
        self._on_released(self.index, int(event.x_root), int(event.y_root))


class _RoiMark(tk.Toplevel):
    """Draggable / resizable OCR region with a step number."""

    def __init__(
        self,
        root: tk.Misc,
        index: int,
        *,
        on_changed: Callable[[int, float, float, float, float], None],
    ) -> None:
        super().__init__(root)
        self.index = index
        self._on_changed = on_changed
        self._anchor: Rect | None = None
        self._mode: str | None = None  # move | se
        self._press_root = (0, 0)
        self._press_norm = (0.0, 0.0, 0.1, 0.1)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "magenta")
        self.configure(bg="magenta")
        self.canvas = tk.Canvas(self, bg="magenta", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._rect = self.canvas.create_rectangle(
            2, 2, 40, 40, outline=QUEUED_OUTLINE, width=2, fill=""
        )
        self._label = self.canvas.create_text(
            12, 12, text=str(index + 1), fill="white", font=("Segoe UI", 10, "bold"), anchor="nw"
        )
        self._grip = self.canvas.create_rectangle(30, 30, 40, 40, fill=QUEUED_FILL, outline=QUEUED_OUTLINE)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.withdraw()

    def set_selected(self, selected: bool) -> None:
        outline = CURRENT_OUTLINE if selected else QUEUED_OUTLINE
        fill = CURRENT_FILL if selected else QUEUED_FILL
        self.canvas.itemconfigure(self._rect, outline=outline)
        self.canvas.itemconfigure(self._grip, fill=fill, outline=outline)

    def set_index_label(self, index: int) -> None:
        self.index = index
        self.canvas.itemconfigure(self._label, text=str(index + 1))

    def show_roi(self, anchor: Rect, nx: float, ny: float, nw: float, nh: float) -> None:
        self._anchor = anchor
        if self._mode:
            return
        left = int(round(anchor.left + nx * max(1, anchor.width - 1)))
        top = int(round(anchor.top + ny * max(1, anchor.height - 1)))
        width = max(36, int(round(nw * max(1, anchor.width - 1))))
        height = max(28, int(round(nh * max(1, anchor.height - 1))))
        self.geometry(f"{width}x{height}+{left}+{top}")
        self.canvas.config(width=width, height=height)
        self.canvas.coords(self._rect, 2, 2, width - 2, height - 2)
        self.canvas.coords(self._grip, width - 14, height - 14, width - 2, height - 2)
        if not self.winfo_viewable():
            self.deiconify()
            self.lift()

    def _press(self, event) -> None:
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        if event.x >= w - 16 and event.y >= h - 16:
            self._mode = "se"
        else:
            self._mode = "move"
        self._press_root = (int(event.x_root), int(event.y_root))
        if self._anchor is None:
            return
        # Recover current norm from geometry.
        ax = self._anchor
        left = self.winfo_x()
        top = self.winfo_y()
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        nx = (left - ax.left) / max(1, ax.width - 1)
        ny = (top - ax.top) / max(1, ax.height - 1)
        nw = width / max(1, ax.width - 1)
        nh = height / max(1, ax.height - 1)
        self._press_norm = (nx, ny, nw, nh)

    def _drag(self, event) -> None:
        if self._anchor is None or self._mode is None:
            return
        ax = self._anchor
        dx = int(event.x_root) - self._press_root[0]
        dy = int(event.y_root) - self._press_root[1]
        nx, ny, nw, nh = self._press_norm
        if self._mode == "move":
            nx = nx + dx / max(1, ax.width - 1)
            ny = ny + dy / max(1, ax.height - 1)
        else:
            nw = nw + dx / max(1, ax.width - 1)
            nh = nh + dy / max(1, ax.height - 1)
        nx = max(0.0, min(0.98, nx))
        ny = max(0.0, min(0.98, ny))
        nw = max(0.04, min(1.0 - nx, nw))
        nh = max(0.04, min(1.0 - ny, nh))
        left = int(round(ax.left + nx * max(1, ax.width - 1)))
        top = int(round(ax.top + ny * max(1, ax.height - 1)))
        width = max(36, int(round(nw * max(1, ax.width - 1))))
        height = max(28, int(round(nh * max(1, ax.height - 1))))
        self.geometry(f"{width}x{height}+{left}+{top}")
        self.canvas.config(width=width, height=height)
        self.canvas.coords(self._rect, 2, 2, width - 2, height - 2)
        self.canvas.coords(self._grip, width - 14, height - 14, width - 2, height - 2)
        self._on_changed(self.index, nx, ny, nw, nh)

    def _release(self, event) -> None:
        self._drag(event)
        self._mode = None


class AtomCreateOverlay:
    """Queue chrome + draggable glyphs while Atom Create owns the Deck."""

    def __init__(
        self,
        root: tk.Misc,
        *,
        on_click_moved: Callable[[int, float, float], None],
        on_click_released: Callable[[int, float, float], None],
        on_drag_moved: Callable[[int, str, float, float], None] | None = None,
        on_drag_released: Callable[[int, str, float, float], None] | None = None,
        on_ocr_changed: Callable[[int, float, float, float, float], None] | None = None,
        on_place_finished: Callable[[], None] | None = None,
        on_place_cancelled: Callable[[int], None] | None = None,
    ) -> None:
        self.root = root
        self._on_click_moved = on_click_moved
        self._on_click_released = on_click_released
        self._on_drag_moved = on_drag_moved or (lambda *_a: None)
        self._on_drag_released = on_drag_released or (lambda *_a: None)
        self._on_ocr_changed = on_ocr_changed or (lambda *_a: None)
        self._on_place_finished = on_place_finished or (lambda: None)
        self._on_place_cancelled = on_place_cancelled or (lambda _i: None)
        self._shown = False
        self._anchor: Rect | None = None
        self._click_marks: list[_ClickMark] = []
        self._click_step_indices: list[int] = []
        self._drag_marks: list[_ClickMark] = []
        self._drag_meta: list[tuple[int, str]] = []  # (step_index, start|end)
        self._roi_marks: list[_RoiMark] = []
        self._roi_step_indices: list[int] = []
        self._place_kind: PlaceKind | None = None
        self._place_step: int | None = None
        self._place_label = ""
        self._place_layer: tk.Toplevel | None = None
        self._place_canvas: tk.Canvas | None = None
        self._place_ghost_win: tk.Toplevel | None = None
        self._place_ghost_canvas: tk.Canvas | None = None
        self._place_ghost_text_id: int | None = None
        self._place_banner: tk.Toplevel | None = None
        self._place_banner_label: tk.Label | None = None
        self._place_line: int | None = None
        self._place_anchor_start: tuple[int, int] | None = None
        self._place_poll: str | None = None

        self.queue = tk.Toplevel(root)
        self.queue.overrideredirect(True)
        self.queue.attributes("-topmost", True)
        self.queue.configure(bg="#141820")
        self.queue.withdraw()
        self._queue_drag: tuple[int, int] | None = None
        self._title = tk.Label(
            self.queue,
            text="Atom queue",
            bg="#141820",
            fg="#F2F6FA",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        self._title.pack(fill="x", padx=10, pady=(8, 2))
        self._title.bind("<ButtonPress-1>", self._queue_press)
        self._title.bind("<B1-Motion>", self._queue_drag_move)
        self._title.bind("<ButtonRelease-1>", self._queue_release)
        self._hint = tk.Label(
            self.queue,
            text="Separate queue window — drag title to move.",
            bg="#141820",
            fg="#7E8796",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=_QUEUE_W - 20,
        )
        self._hint.pack(fill="x", padx=10, pady=(0, 6))
        self._list = tk.Text(
            self.queue,
            width=34,
            height=14,
            bg="#0E1218",
            fg="#D8E2EC",
            insertbackground="#D8E2EC",
            relief="flat",
            font=("Consolas", 10),
            state="disabled",
        )
        self._list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._list.tag_configure("sel", foreground="#7CF0B8", background="#243040")
        self._list.tag_configure("muted", foreground="#7E8796")
        self._list.tag_configure("detail", foreground="#9AA4B2")
        self._list.tag_configure("section", foreground="#F0C070")
        self._list.tag_configure("phase_active", foreground="#7CF0B8")
        self._list.tag_configure("expand", foreground="#9EC5FF")
        self._queue_placed_once = False
        self._avoid: Rect | None = None
        self._show_details = False
        self._draft_kind = "automation"
        self._map_phases: list[dict[str, Any]] = []
        self._map_home = ""
        self._map_active = ""
        self._map_group = ""
        self._map_group_type = ""

    @property
    def shown(self) -> bool:
        return self._shown

    @property
    def placing(self) -> bool:
        return self._place_kind is not None

    @property
    def place_kind(self) -> PlaceKind | None:
        return self._place_kind

    def show(self) -> None:
        if self._shown:
            return
        self._place_queue()
        self.queue.deiconify()
        self.queue.lift()
        self._shown = True

    def hide(self) -> None:
        self.cancel_place(remove_step=False)
        self.clear_marks()
        if self._shown:
            try:
                self.queue.withdraw()
            except Exception:
                pass
        self._shown = False
        self._anchor = None
        self._queue_placed_once = False

    def destroy(self) -> None:
        self.hide()
        try:
            self.queue.destroy()
        except Exception:
            pass

    def begin_place_click(self, step_index: int, *, label: str = "") -> None:
        self._start_place("click", step_index, label=label or f"{step_index + 1}")

    def begin_place_drag(self, step_index: int, *, label: str = "") -> None:
        self._start_place("drag_start", step_index, label=label or f"{step_index + 1}a")

    def confirm_place_at_cursor(self) -> bool:
        """Space / Deck confirm — drop at current cursor if placing."""

        if not self.placing:
            return False
        x, y = win32_api.cursor_pos()
        self._drop_at_screen(x, y)
        return True

    def cancel_place(self, *, remove_step: bool = True) -> bool:
        if not self.placing:
            return False
        step = self._place_step
        self._teardown_place_layer()
        if remove_step and step is not None:
            self._on_place_cancelled(step)
        return True

    def sync(
        self,
        *,
        steps: list[dict[str, Any]],
        selected_index: int,
        phase: str,
        anchor: Rect | None,
        avoid: Rect | None = None,
        show_details: bool = False,
        draft_kind: str = "automation",
        map_phases: list[dict[str, Any]] | None = None,
        home_phase: str = "",
        active_phase: str = "",
        active_group: str = "",
        active_group_type: str = "",
    ) -> None:
        if not self._shown:
            self.show()
        self._anchor = anchor
        self._avoid = avoid
        self._show_details = bool(show_details)
        self._draft_kind = str(draft_kind or "automation")
        self._map_phases = list(map_phases or [])
        self._map_home = str(home_phase or "")
        self._map_active = str(active_phase or "")
        self._map_group = str(active_group or "")
        self._map_group_type = str(active_group_type or "")
        self._place_queue()
        self._paint_queue(steps, selected_index, phase)
        self._sync_click_marks(steps, selected_index, anchor)
        self._sync_drag_marks(steps, selected_index, anchor)
        self._sync_roi_marks(steps, selected_index, anchor)
        if self.placing:
            kind = self._place_kind or "click"
            if kind == "drag_start":
                what = "DRAG START"
            elif kind == "drag_end":
                what = "DRAG END"
            else:
                what = "CLICK"
            self._title.configure(text=f"Atom queue · PLACING {what}")
            self._hint.configure(
                text=f"PLACING {what} — left-click or Space drops · Esc cancels place (stays in Create)."
            )
            try:
                self.queue.lift()
            except Exception:
                pass

    def _step_is_placing(self, step: dict[str, Any], index: int) -> bool:
        if self._place_step is not None and index == self._place_step:
            return True
        return bool(step.get("placing"))

    def _rects_overlap(self, a: Rect, left: int, top: int, width: int, height: int) -> bool:
        right = left + width
        bottom = top + height
        return not (right <= a.left or left >= a.right or bottom <= a.top or top >= a.bottom)

    def _queue_wh(self) -> tuple[int, int]:
        if self._draft_kind == "phase_map":
            return _QUEUE_W, _QUEUE_H_PHASE
        return _QUEUE_W, _QUEUE_H

    def _place_queue(self) -> None:
        qw, qh = self._queue_wh()
        if self._queue_placed_once and self._queue_drag is None:
            try:
                geo = self.queue.geometry()
                if "+" in geo:
                    _, rest = geo.split("+", 1)
                    parts = rest.split("+")
                    if len(parts) >= 2:
                        x, y = int(parts[0]), int(parts[1])
                        self.queue.geometry(f"{qw}x{qh}+{x}+{y}")
                        return
            except Exception:
                pass
        screen = win32_api.virtual_screen()
        candidates: list[tuple[int, int]] = []
        avoid = getattr(self, "_avoid", None)
        if self._anchor is not None:
            # Prefer beside the game, not on top of the Flight Deck.
            candidates.extend(
                [
                    (self._anchor.left - qw - 12, self._anchor.top),
                    (self._anchor.right + 12, self._anchor.top),
                    (self._anchor.left, self._anchor.bottom + 12),
                ]
            )
        if avoid is not None:
            candidates.extend(
                [
                    (avoid.left - qw - 12, avoid.top),
                    (avoid.right + 12, avoid.top),
                    (avoid.left, avoid.bottom + 12),
                    (avoid.left, avoid.top - qh - 12),
                ]
            )
        candidates.append((screen.left + 24, screen.top + 80))
        chosen: tuple[int, int] | None = None
        for x, y in candidates:
            x = max(screen.left + 8, min(x, screen.right - qw - 8))
            y = max(screen.top + 8, min(y, screen.bottom - qh - 8))
            if avoid is not None and self._rects_overlap(avoid, x, y, qw, qh):
                continue
            chosen = (x, y)
            break
        if chosen is None:
            # Last resort: below the deck if present, else screen corner.
            if avoid is not None:
                x = max(screen.left + 8, min(avoid.left, screen.right - qw - 8))
                y = max(screen.top + 8, min(avoid.bottom + 12, screen.bottom - qh - 8))
                chosen = (x, y)
            else:
                chosen = (screen.left + 24, screen.top + 80)
        self.queue.geometry(f"{qw}x{qh}+{chosen[0]}+{chosen[1]}")
        self._queue_placed_once = True

    def _queue_press(self, event) -> None:
        self._queue_drag = (int(event.x_root), int(event.y_root))

    def _queue_drag_move(self, event) -> None:
        if self._queue_drag is None:
            return
        dx = int(event.x_root) - self._queue_drag[0]
        dy = int(event.y_root) - self._queue_drag[1]
        self._queue_drag = (int(event.x_root), int(event.y_root))
        try:
            qw, qh = self._queue_wh()
            x = int(self.queue.winfo_x()) + dx
            y = int(self.queue.winfo_y()) + dy
            self.queue.geometry(f"{qw}x{qh}+{x}+{y}")
        except Exception:
            pass

    def _queue_release(self, _event) -> None:
        self._queue_drag = None

    def _paint_queue(self, steps: list[dict[str, Any]], selected: int, phase: str) -> None:
        if self._draft_kind == "phase_map":
            self._paint_phase_map_queue(steps, selected, phase)
            return
        phase_key = str(phase).lower()
        if phase_key == "edit":
            phase_label = "EDIT"
        elif phase_key == "playbook":
            phase_label = "PLAYBOOK"
        elif phase_key == "kind":
            phase_label = "KIND"
        else:
            phase_label = "CREATE"
        self._title.configure(text=f"Atom queue · {phase_label}")
        show_details = bool(getattr(self, "_show_details", False))
        section_ranges: list[tuple[int, int]] = []
        detail_ranges: list[tuple[int, int]] = []
        expand_ranges: list[tuple[int, int]] = []
        active_ranges: list[tuple[int, int]] = []
        if not steps:
            body = "(empty — B expands gestures · P opens playbook · E edits)\n"
            sel_line = None
        else:
            lines: list[str] = []
            sel_line = None
            for i, step in enumerate(steps):
                mark = "▶" if i == selected else " "
                lines.append(f"{mark} {i + 1}. {step_label(step)}")
                if i == selected:
                    sel_line = len(lines)
                if show_details:
                    start = len(lines) + 1
                    for detail in step_detail_lines(step):
                        lines.append(f"    {detail}")
                    end = len(lines)
                    if end >= start:
                        detail_ranges.append((start, end))
            body = "\n".join(lines) + "\n"
        self._apply_queue_text(
            body,
            sel_line=sel_line,
            detail_ranges=detail_ranges,
            section_ranges=section_ranges,
            expand_ranges=expand_ranges,
            active_ranges=active_ranges,
        )
        if self._anchor is None:
            self._hint.configure(text="Anchor a window to place glyphs. Queue still works.")
        elif phase_key == "edit":
            self._hint.configure(
                text="W/S select · R/F reorder · 0 remove · type leaves edit fields · D details."
            )
        elif phase_key == "kind":
            self._hint.configure(text="Choose 1 Automation or 2 Phase map. Queue waits.")
        else:
            hint = "Drag marks / ROI on the game. Esc peels Playbook → Create → save."
            if show_details:
                hint = "D details on — event fields listed under each step. " + hint
            self._hint.configure(text=hint)

    def _paint_phase_map_queue(
        self, steps: list[dict[str, Any]], selected: int, phase: str
    ) -> None:
        phase_key = str(phase).lower()
        mode = {
            "edit": "EDIT",
            "phase_map": "MAP",
            "kind": "KIND",
        }.get(phase_key, "MAP")
        self._title.configure(text=f"Phase map queue · {mode}")

        lines: list[str] = []
        section_ranges: list[tuple[int, int]] = []
        detail_ranges: list[tuple[int, int]] = []
        expand_ranges: list[tuple[int, int]] = []
        active_ranges: list[tuple[int, int]] = []
        sel_line: int | None = None
        show_details = bool(getattr(self, "_show_details", False))

        def add_section(title: str) -> None:
            lines.append(title)
            section_ranges.append((len(lines), len(lines)))

        # Context strip
        group = self._map_group or "—"
        gtype = self._map_group_type or "—"
        active = self._map_active or "—"
        home = self._map_home or "—"
        lines.append(f"active {active} · home {home}")
        lines.append(f"group {group} ({gtype})")
        lines.append("")

        add_section("PHASES")
        tree = format_phase_tree_lines(
            self._map_phases,
            home_phase=self._map_home,
            active_phase=self._map_active,
        )
        for row in tree:
            lines.append(row)
            if "active" in row:
                active_ranges.append((len(lines), len(lines)))
        lines.append("")

        add_section("PIECES")
        if not steps:
            lines.append("  (empty — G enter key · S scroll · T target)")
        else:
            # Group under phase headers so the queue reads like the screen map.
            by_phase: dict[str, list[int]] = {}
            order: list[str] = []
            for i, step in enumerate(steps):
                pid = str(step.get("phase") or "(unbound)")
                if pid not in by_phase:
                    by_phase[pid] = []
                    order.append(pid)
                by_phase[pid].append(i)
            # Prefer declared phase order, then leftovers.
            preferred = [str(p.get("id") or "") for p in self._map_phases if p.get("id")]
            ordered_phases = [p for p in preferred if p in by_phase]
            ordered_phases.extend(p for p in order if p not in ordered_phases)

            for pid in ordered_phases:
                header = f"  · {pid}"
                if pid == self._map_active:
                    header += " ●"
                if pid == self._map_home:
                    header += " ★"
                lines.append(header)
                section_ranges.append((len(lines), len(lines)))
                if pid == self._map_active:
                    active_ranges.append((len(lines), len(lines)))
                for i in by_phase[pid]:
                    step = steps[i]
                    lines.append(queue_piece_line(step, index=i, selected=(i == selected)))
                    if i == selected:
                        sel_line = len(lines)
                        if str(step.get("role")) == "target":
                            scrolls = list(step.get("scrolls") or [])
                            preview = "    expand: enter → "
                            if scrolls:
                                preview += "scroll(" + ",".join(str(s) for s in scrolls) + ") → "
                            preview += "act"
                            lines.append(preview)
                            expand_ranges.append((len(lines), len(lines)))
                        if show_details:
                            start = len(lines) + 1
                            for detail in step_detail_lines(step):
                                lines.append(f"    {detail}")
                            end = len(lines)
                            if end >= start:
                                detail_ranges.append((start, end))

        body = "\n".join(lines) + "\n"
        self._apply_queue_text(
            body,
            sel_line=sel_line,
            detail_ranges=detail_ranges,
            section_ranges=section_ranges,
            expand_ranges=expand_ranges,
            active_ranges=active_ranges,
        )
        if self._anchor is None:
            self._hint.configure(text="Anchor a window to place glyphs. Phase tree still shows here.")
        elif phase_key == "edit":
            self._hint.configure(
                text="W/S select pieces · scrolls keep drag Speed/Pause · D details."
            )
        else:
            self._hint.configure(
                text="Phases live in this queue. G/H/T/S place pieces · X expand preview · D details."
            )

    def _apply_queue_text(
        self,
        body: str,
        *,
        sel_line: int | None,
        detail_ranges: list[tuple[int, int]],
        section_ranges: list[tuple[int, int]],
        expand_ranges: list[tuple[int, int]],
        active_ranges: list[tuple[int, int]],
    ) -> None:
        self._list.configure(state="normal")
        self._list.delete("1.0", "end")
        self._list.insert("1.0", body)
        for start, end in section_ranges:
            self._list.tag_add("section", f"{start}.0", f"{end}.end")
        for start, end in detail_ranges:
            self._list.tag_add("detail", f"{start}.0", f"{end}.end")
        for start, end in expand_ranges:
            self._list.tag_add("expand", f"{start}.0", f"{end}.end")
        for start, end in active_ranges:
            self._list.tag_add("phase_active", f"{start}.0", f"{end}.end")
        if sel_line is not None:
            self._list.tag_add("sel", f"{sel_line}.0", f"{sel_line}.end")
            try:
                self._list.see(f"{sel_line}.0")
            except Exception:
                pass
        self._list.configure(state="disabled")
        try:
            self.queue.lift()
        except Exception:
            pass

    def _start_place(self, kind: PlaceKind, step_index: int, *, label: str) -> None:
        self.cancel_place(remove_step=False)
        if self._anchor is None:
            return
        self._place_kind = kind
        self._place_step = int(step_index)
        self._place_label = label
        self._place_anchor_start = None
        if kind == "drag_end" and 0 <= step_index:
            # Caller should have set start coords already; remember screen start for rubber-band.
            pass
        self._ensure_place_layer()
        self._poll_place_cursor()

    def _place_banner_text(self) -> str:
        kind = self._place_kind or "click"
        if kind == "drag_start":
            return "PLACING DRAG START — left-click or Space drops start · Esc cancels (stay in Create)"
        if kind == "drag_end":
            return "PLACING DRAG END — left-click or Space drops end · Esc cancels (stay in Create)"
        return "PLACING CLICK — left-click or Space drops here · Esc cancels (stay in Create)"

    def _ensure_place_layer(self) -> None:
        anchor = self._anchor
        if anchor is None:
            return
        if self._place_layer is None:
            layer = tk.Toplevel(self.root)
            layer.overrideredirect(True)
            layer.attributes("-topmost", True)
            try:
                # Near-invisible catcher — opaque ghost + banner carry the affordance.
                layer.attributes("-alpha", 0.01)
            except Exception:
                pass
            layer.configure(bg="#101820")
            canvas = tk.Canvas(layer, highlightthickness=0, bd=0, bg="#101820")
            canvas.pack(fill="both", expand=True)
            canvas.bind("<ButtonPress-1>", self._place_button)
            canvas.bind("<Motion>", self._place_motion)
            layer.bind("<Escape>", lambda _e: self.cancel_place(remove_step=True))
            layer.bind("<space>", lambda _e: self.confirm_place_at_cursor())
            layer.bind("<Return>", lambda _e: self.confirm_place_at_cursor())
            layer.bind("<KeyPress-space>", lambda _e: self.confirm_place_at_cursor())
            layer.bind("<KeyPress-Return>", lambda _e: self.confirm_place_at_cursor())
            self._place_layer = layer
            self._place_canvas = canvas
            self._place_line = canvas.create_line(
                0, 0, 0, 0, fill=CURRENT_OUTLINE, width=3, state="hidden"
            )

            ghost = tk.Toplevel(self.root)
            ghost.overrideredirect(True)
            ghost.attributes("-topmost", True)
            ghost.attributes("-transparentcolor", "magenta")
            ghost.configure(bg="magenta")
            gcanvas = tk.Canvas(
                ghost, width=_GHOST, height=_GHOST, bg="magenta", highlightthickness=0, bd=0
            )
            gcanvas.pack()
            gcanvas.create_oval(
                2, 2, _GHOST - 2, _GHOST - 2, outline=CURRENT_OUTLINE, width=3, fill=CURRENT_FILL
            )
            self._place_ghost_text_id = gcanvas.create_text(
                _GHOST // 2,
                _GHOST // 2,
                text="•",
                fill="white",
                font=("Segoe UI", 11, "bold"),
            )
            self._place_ghost_canvas = gcanvas
            self._place_ghost_win = ghost

            banner = tk.Toplevel(self.root)
            banner.overrideredirect(True)
            banner.attributes("-topmost", True)
            banner.configure(bg="#184838")
            blabel = tk.Label(
                banner,
                text=self._place_banner_text(),
                bg="#184838",
                fg="#F2F6FA",
                font=("Segoe UI", 11, "bold"),
                anchor="w",
                padx=12,
                pady=8,
            )
            blabel.pack(fill="both", expand=True)
            self._place_banner = banner
            self._place_banner_label = blabel

        layer = self._place_layer
        assert layer is not None and self._place_canvas is not None
        layer.geometry(
            f"{max(1, anchor.width)}x{max(1, anchor.height)}+{anchor.left}+{anchor.top}"
        )
        self._place_canvas.config(width=anchor.width, height=anchor.height)
        label = self._place_label or "•"
        if getattr(self, "_place_ghost_canvas", None) is not None:
            self._place_ghost_canvas.itemconfigure(self._place_ghost_text_id, text=label[:4])
        if self._place_banner is not None:
            bh = 40
            self._place_banner.geometry(
                f"{max(1, anchor.width)}x{bh}+{anchor.left}+{anchor.top}"
            )
            if self._place_banner_label is not None:
                self._place_banner_label.configure(text=self._place_banner_text())
            try:
                self._place_banner.deiconify()
                self._place_banner.lift()
            except Exception:
                pass
        try:
            layer.deiconify()
            layer.lift()
            layer.focus_force()
        except Exception:
            pass
        if self._place_ghost_win is not None:
            try:
                self._place_ghost_win.deiconify()
                self._place_ghost_win.lift()
            except Exception:
                pass
        try:
            self.queue.lift()
        except Exception:
            pass

    def _teardown_place_layer(self) -> None:
        if self._place_poll is not None:
            try:
                self.root.after_cancel(self._place_poll)
            except Exception:
                pass
            self._place_poll = None
        self._place_kind = None
        self._place_step = None
        self._place_label = ""
        self._place_anchor_start = None
        layer = self._place_layer
        ghost = self._place_ghost_win
        banner = self._place_banner
        self._place_layer = None
        self._place_canvas = None
        self._place_ghost_win = None
        self._place_ghost_canvas = None
        self._place_ghost_text_id = None
        self._place_banner = None
        self._place_banner_label = None
        self._place_line = None
        for win in (layer, ghost, banner):
            if win is None:
                continue
            try:
                win.destroy()
            except Exception:
                pass

    def _poll_place_cursor(self) -> None:
        if not self.placing or self._anchor is None:
            return
        x, y = win32_api.cursor_pos()
        self._move_ghost_to_screen(x, y)
        self._place_poll = self.root.after(16, self._poll_place_cursor)

    def _place_motion(self, event) -> None:
        if self._anchor is None:
            return
        self._move_ghost_to_screen(self._anchor.left + int(event.x), self._anchor.top + int(event.y))

    def _move_ghost_to_screen(self, screen_x: int, screen_y: int) -> None:
        ghost = self._place_ghost_win
        canvas = self._place_canvas
        anchor = self._anchor
        if ghost is not None:
            left = int(screen_x) - _GHOST // 2
            top = int(screen_y) - _GHOST // 2
            try:
                ghost.geometry(f"{_GHOST}x{_GHOST}+{left}+{top}")
                if not ghost.winfo_viewable():
                    ghost.deiconify()
                ghost.lift()
            except Exception:
                pass
        if (
            canvas is not None
            and anchor is not None
            and self._place_kind == "drag_end"
            and self._place_line is not None
            and self._place_anchor_start is not None
        ):
            sx, sy = self._place_anchor_start
            lx = int(screen_x) - int(anchor.left)
            ly = int(screen_y) - int(anchor.top)
            canvas.itemconfigure(self._place_line, state="normal")
            canvas.coords(self._place_line, sx - anchor.left, sy - anchor.top, lx, ly)
        elif canvas is not None and self._place_line is not None:
            canvas.itemconfigure(self._place_line, state="hidden")

    def _place_button(self, event) -> None:
        if self._anchor is None:
            return
        self._drop_at_screen(self._anchor.left + int(event.x), self._anchor.top + int(event.y))

    def _drop_at_screen(self, screen_x: int, screen_y: int) -> None:
        if not self.placing or self._place_step is None:
            return
        coords = self._screen_to_nx_ny(screen_x, screen_y)
        if coords is None:
            return
        nx, ny = coords
        kind = self._place_kind
        step = self._place_step
        if kind == "click":
            self._teardown_place_layer()
            self._on_click_released(step, nx, ny)
            self._on_place_finished()
            return
        if kind == "drag_start":
            self._on_drag_released(step, "start", nx, ny)
            self._place_anchor_start = (int(screen_x), int(screen_y))
            self._place_kind = "drag_end"
            self._place_label = f"{step + 1}b"
            if self._place_ghost_canvas is not None and self._place_ghost_text_id is not None:
                self._place_ghost_canvas.itemconfigure(
                    self._place_ghost_text_id, text=self._place_label[:4]
                )
            if self._place_banner_label is not None:
                self._place_banner_label.configure(text=self._place_banner_text())
            self._on_place_finished()  # refresh queue mid-drag
            return
        if kind == "drag_end":
            self._teardown_place_layer()
            self._on_drag_released(step, "end", nx, ny)
            self._on_place_finished()

    def _sync_click_marks(
        self,
        steps: list[dict[str, Any]],
        selected: int,
        anchor: Rect | None,
    ) -> None:
        click_indices = [
            i
            for i, step in enumerate(steps)
            if str(step.get("type")) == "click" and not self._step_is_placing(step, i)
        ]
        if anchor is None or not click_indices:
            self._clear_click_marks()
            return
        while len(self._click_marks) < len(click_indices):
            mark = _ClickMark(
                self.root,
                len(self._click_marks),
                on_moved=self._click_mark_moved,
                on_released=self._click_mark_released,
            )
            self._click_marks.append(mark)
        while len(self._click_marks) > len(click_indices):
            self._click_marks.pop().destroy()
        self._click_step_indices = list(click_indices)
        width = max(1, anchor.width)
        height = max(1, anchor.height)
        for mark_i, step_i in enumerate(click_indices):
            step = steps[step_i]
            nx = float(step.get("nx", 0.5))
            ny = float(step.get("ny", 0.5))
            sx = int(round(anchor.left + nx * (width - 1)))
            sy = int(round(anchor.top + ny * (height - 1)))
            mark = self._click_marks[mark_i]
            role = str(step.get("role") or "")
            if role and self._draft_kind == "phase_map":
                glyph = role_glyph(role)
                mark.set_index_label(step_i, text=f"{glyph}{step_i + 1}")
            else:
                mark.set_index_label(step_i)
            mark.set_selected(step_i == selected)
            mark.show_at(sx, sy)

    def _sync_drag_marks(
        self,
        steps: list[dict[str, Any]],
        selected: int,
        anchor: Rect | None,
    ) -> None:
        meta: list[tuple[int, str]] = []
        for i, step in enumerate(steps):
            if str(step.get("type")) != "drag":
                continue
            placing = self._step_is_placing(step, i)
            # While placing start: hide both. While placing end: show start only.
            if placing and self._place_kind == "drag_start":
                continue
            meta.append((i, "start"))
            if not (placing and self._place_kind == "drag_end"):
                meta.append((i, "end"))
        if anchor is None or not meta:
            self._clear_drag_marks()
            return
        while len(self._drag_marks) < len(meta):
            mark = _ClickMark(
                self.root,
                len(self._drag_marks),
                on_moved=self._drag_mark_moved,
                on_released=self._drag_mark_released,
            )
            self._drag_marks.append(mark)
        while len(self._drag_marks) > len(meta):
            self._drag_marks.pop().destroy()
        self._drag_meta = list(meta)
        width = max(1, anchor.width)
        height = max(1, anchor.height)
        for mark_i, (step_i, which) in enumerate(meta):
            step = steps[step_i]
            if which == "end":
                nx = float(step.get("nx1", 0.6))
                ny = float(step.get("ny1", 0.5))
                label = f"{step_i + 1}b"
            else:
                nx = float(step.get("nx0", 0.4))
                ny = float(step.get("ny0", 0.5))
                label = f"{step_i + 1}a"
            sx = int(round(anchor.left + nx * (width - 1)))
            sy = int(round(anchor.top + ny * (height - 1)))
            mark = self._drag_marks[mark_i]
            mark.set_index_label(mark_i, text=label)
            mark.set_selected(step_i == selected)
            mark.show_at(sx, sy)

    def _sync_roi_marks(
        self,
        steps: list[dict[str, Any]],
        selected: int,
        anchor: Rect | None,
    ) -> None:
        roi_indices = [i for i, step in enumerate(steps) if str(step.get("type")) == "ocr"]
        if anchor is None or not roi_indices:
            self._clear_roi_marks()
            return
        while len(self._roi_marks) < len(roi_indices):
            mark = _RoiMark(
                self.root,
                len(self._roi_marks),
                on_changed=self._roi_changed,
            )
            self._roi_marks.append(mark)
        while len(self._roi_marks) > len(roi_indices):
            self._roi_marks.pop().destroy()
        self._roi_step_indices = list(roi_indices)
        for mark_i, step_i in enumerate(roi_indices):
            step = steps[step_i]
            mark = self._roi_marks[mark_i]
            mark.set_index_label(step_i)
            mark.set_selected(step_i == selected)
            mark.show_roi(
                anchor,
                float(step.get("nx", 0.35)),
                float(step.get("ny", 0.35)),
                float(step.get("nw", 0.30)),
                float(step.get("nh", 0.12)),
            )

    def clear_marks(self) -> None:
        self._clear_click_marks()
        self._clear_drag_marks()
        self._clear_roi_marks()

    def _clear_click_marks(self) -> None:
        for mark in self._click_marks:
            try:
                mark.destroy()
            except Exception:
                pass
        self._click_marks = []
        self._click_step_indices = []

    def _clear_drag_marks(self) -> None:
        for mark in self._drag_marks:
            try:
                mark.destroy()
            except Exception:
                pass
        self._drag_marks = []
        self._drag_meta = []

    def _clear_roi_marks(self) -> None:
        for mark in self._roi_marks:
            try:
                mark.destroy()
            except Exception:
                pass
        self._roi_marks = []
        self._roi_step_indices = []

    def _screen_to_nx_ny(self, screen_x: int, screen_y: int) -> tuple[float, float] | None:
        anchor = self._anchor
        if anchor is None:
            return None
        width = max(1, anchor.width)
        height = max(1, anchor.height)
        nx = (float(screen_x) - float(anchor.left)) / float(width - 1 or 1)
        ny = (float(screen_y) - float(anchor.top)) / float(height - 1 or 1)
        return max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))

    def _click_mark_moved(self, mark_index: int, screen_x: int, screen_y: int) -> None:
        if mark_index < 0 or mark_index >= len(self._click_step_indices):
            return
        coords = self._screen_to_nx_ny(screen_x, screen_y)
        if coords is None:
            return
        self._on_click_moved(self._click_step_indices[mark_index], coords[0], coords[1])

    def _click_mark_released(self, mark_index: int, screen_x: int, screen_y: int) -> None:
        if mark_index < 0 or mark_index >= len(self._click_step_indices):
            return
        coords = self._screen_to_nx_ny(screen_x, screen_y)
        if coords is None:
            return
        self._on_click_released(self._click_step_indices[mark_index], coords[0], coords[1])

    def _drag_mark_moved(self, mark_index: int, screen_x: int, screen_y: int) -> None:
        if mark_index < 0 or mark_index >= len(self._drag_meta):
            return
        coords = self._screen_to_nx_ny(screen_x, screen_y)
        if coords is None:
            return
        step_i, which = self._drag_meta[mark_index]
        self._on_drag_moved(step_i, which, coords[0], coords[1])

    def _drag_mark_released(self, mark_index: int, screen_x: int, screen_y: int) -> None:
        if mark_index < 0 or mark_index >= len(self._drag_meta):
            return
        coords = self._screen_to_nx_ny(screen_x, screen_y)
        if coords is None:
            return
        step_i, which = self._drag_meta[mark_index]
        self._on_drag_released(step_i, which, coords[0], coords[1])

    def _roi_changed(self, mark_index: int, nx: float, ny: float, nw: float, nh: float) -> None:
        if mark_index < 0 or mark_index >= len(self._roi_step_indices):
            return
        self._on_ocr_changed(self._roi_step_indices[mark_index], nx, ny, nw, nh)
