"""Atom Create visual layer — queue panel + click/drag/OCR glyphs on the anchor."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

from idle_lab.models import Rect
from idle_lab.shared_overlay.primitives import (
    CURRENT_FILL,
    CURRENT_OUTLINE,
    QUEUED_FILL,
    QUEUED_OUTLINE,
)
from idle_lab.shell.atom_create import step_detail_lines, step_label
from idle_lab import win32_api

_MARKER = 30
_QUEUE_W = 280
_QUEUE_H = 320


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
    ) -> None:
        self.root = root
        self._on_click_moved = on_click_moved
        self._on_click_released = on_click_released
        self._on_drag_moved = on_drag_moved or (lambda *_a: None)
        self._on_drag_released = on_drag_released or (lambda *_a: None)
        self._on_ocr_changed = on_ocr_changed or (lambda *_a: None)
        self._shown = False
        self._anchor: Rect | None = None
        self._click_marks: list[_ClickMark] = []
        self._click_step_indices: list[int] = []
        self._drag_marks: list[_ClickMark] = []
        self._drag_meta: list[tuple[int, str]] = []  # (step_index, start|end)
        self._roi_marks: list[_RoiMark] = []
        self._roi_step_indices: list[int] = []

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
        self._queue_placed_once = False
        self._avoid: Rect | None = None
        self._show_details = False

    @property
    def shown(self) -> bool:
        return self._shown

    def show(self) -> None:
        if self._shown:
            return
        self._place_queue()
        self.queue.deiconify()
        self.queue.lift()
        self._shown = True

    def hide(self) -> None:
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

    def sync(
        self,
        *,
        steps: list[dict[str, Any]],
        selected_index: int,
        phase: str,
        anchor: Rect | None,
        avoid: Rect | None = None,
        show_details: bool = False,
    ) -> None:
        if not self._shown:
            self.show()
        self._anchor = anchor
        self._avoid = avoid
        self._show_details = bool(show_details)
        self._place_queue()
        self._paint_queue(steps, selected_index, phase)
        self._sync_click_marks(steps, selected_index, anchor)
        self._sync_drag_marks(steps, selected_index, anchor)
        self._sync_roi_marks(steps, selected_index, anchor)

    def _rects_overlap(self, a: Rect, left: int, top: int, width: int, height: int) -> bool:
        right = left + width
        bottom = top + height
        return not (right <= a.left or left >= a.right or bottom <= a.top or top >= a.bottom)

    def _place_queue(self) -> None:
        if self._queue_placed_once and self._queue_drag is None:
            try:
                geo = self.queue.geometry()
                if "+" in geo:
                    _, rest = geo.split("+", 1)
                    parts = rest.split("+")
                    if len(parts) >= 2:
                        x, y = int(parts[0]), int(parts[1])
                        self.queue.geometry(f"{_QUEUE_W}x{_QUEUE_H}+{x}+{y}")
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
                    (self._anchor.left - _QUEUE_W - 12, self._anchor.top),
                    (self._anchor.right + 12, self._anchor.top),
                    (self._anchor.left, self._anchor.bottom + 12),
                ]
            )
        if avoid is not None:
            candidates.extend(
                [
                    (avoid.left - _QUEUE_W - 12, avoid.top),
                    (avoid.right + 12, avoid.top),
                    (avoid.left, avoid.bottom + 12),
                    (avoid.left, avoid.top - _QUEUE_H - 12),
                ]
            )
        candidates.append((screen.left + 24, screen.top + 80))
        chosen: tuple[int, int] | None = None
        for x, y in candidates:
            x = max(screen.left + 8, min(x, screen.right - _QUEUE_W - 8))
            y = max(screen.top + 8, min(y, screen.bottom - _QUEUE_H - 8))
            if avoid is not None and self._rects_overlap(avoid, x, y, _QUEUE_W, _QUEUE_H):
                continue
            chosen = (x, y)
            break
        if chosen is None:
            # Last resort: below the deck if present, else screen corner.
            if avoid is not None:
                x = max(screen.left + 8, min(avoid.left, screen.right - _QUEUE_W - 8))
                y = max(screen.top + 8, min(avoid.bottom + 12, screen.bottom - _QUEUE_H - 8))
                chosen = (x, y)
            else:
                chosen = (screen.left + 24, screen.top + 80)
        self.queue.geometry(f"{_QUEUE_W}x{_QUEUE_H}+{chosen[0]}+{chosen[1]}")
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
            x = int(self.queue.winfo_x()) + dx
            y = int(self.queue.winfo_y()) + dy
            self.queue.geometry(f"{_QUEUE_W}x{_QUEUE_H}+{x}+{y}")
        except Exception:
            pass

    def _queue_release(self, _event) -> None:
        self._queue_drag = None

    def _paint_queue(self, steps: list[dict[str, Any]], selected: int, phase: str) -> None:
        phase_key = str(phase).lower()
        if phase_key == "edit":
            phase_label = "EDIT"
        elif phase_key == "playbook":
            phase_label = "PLAYBOOK"
        else:
            phase_label = "CREATE"
        self._title.configure(text=f"Atom queue · {phase_label}")
        show_details = bool(getattr(self, "_show_details", False))
        if not steps:
            body = "(empty — B expands gestures · P opens playbook · E edits)\n"
            detail_ranges: list[tuple[int, int]] = []
            sel_line = None
        else:
            lines: list[str] = []
            detail_ranges = []
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
        self._list.configure(state="normal")
        self._list.delete("1.0", "end")
        self._list.insert("1.0", body)
        for start, end in detail_ranges:
            self._list.tag_add("detail", f"{start}.0", f"{end}.end")
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
        if self._anchor is None:
            self._hint.configure(text="Anchor a window to place glyphs. Queue still works.")
        elif phase_key == "edit":
            self._hint.configure(
                text="W/S select · R/F reorder · 0 remove · type leaves edit fields · D details."
            )
        else:
            hint = "Drag marks / ROI on the game. Esc peels Playbook → Create → save."
            if show_details:
                hint = "D details on — event fields listed under each step. " + hint
            self._hint.configure(text=hint)

    def _sync_click_marks(
        self,
        steps: list[dict[str, Any]],
        selected: int,
        anchor: Rect | None,
    ) -> None:
        click_indices = [i for i, step in enumerate(steps) if str(step.get("type")) == "click"]
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
            meta.append((i, "start"))
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
