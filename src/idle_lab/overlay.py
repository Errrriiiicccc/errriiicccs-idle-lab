"""Click-through frame around the anchored window, plus draggable point markers."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from idle_lab.models import Rect
from idle_lab import win32_api

MARKER = 26


class Marker(tk.Toplevel):
    def __init__(self, root: tk.Misc, index: int, on_moved, on_released) -> None:
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
            width=MARKER,
            height=MARKER,
            bg="magenta",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.create_oval(2, 2, MARKER - 2, MARKER - 2, fill="#12343c", outline="#3CE6FF", width=2)
        self.canvas.create_text(
            MARKER // 2,
            MARKER // 2,
            text=str(index + 1),
            fill="white",
            font=("Segoe UI", 9, "bold"),
        )
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.withdraw()

    def show_at(self, screen_x: int, screen_y: int) -> None:
        if self.dragging:
            return
        left = int(screen_x) - MARKER // 2
        top = int(screen_y) - MARKER // 2
        self.geometry(f"{MARKER}x{MARKER}+{left}+{top}")
        if not self.winfo_viewable():
            self.deiconify()
            self.lift()

    def _press(self, _event) -> None:
        self.dragging = True

    def _drag(self, event) -> None:
        self.dragging = True
        left = int(event.x_root) - MARKER // 2
        top = int(event.y_root) - MARKER // 2
        self.geometry(f"{MARKER}x{MARKER}+{left}+{top}")
        self._on_moved(self.index, int(event.x_root), int(event.y_root))

    def _release(self, event) -> None:
        self.dragging = False
        self._on_released(self.index, int(event.x_root), int(event.y_root))


class Overlay:
    def __init__(self, root: tk.Misc, on_moved: Callable, on_released: Callable) -> None:
        self.root = root
        self._on_moved = on_moved
        self._on_released = on_released
        self._shown = False
        self._vs: Rect | None = None
        self._frame_rect: Rect | None = None
        self._frame_vs: Rect | None = None
        self._markers: list[Marker] = []
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
        self.clear_markers()
        self.win.destroy()

    def set_visible(self, visible: bool) -> None:
        if visible and not self._shown:
            self._sync_geometry()
            self.win.deiconify()
            self.win.update_idletasks()
            self._apply_styles()
            self._shown = True
        elif not visible and self._shown:
            self.win.withdraw()
            self.clear_markers()
            self._frame_rect = None
            self._frame_vs = None
            self._shown = False

    def set_frame(self, rect: Rect | None) -> None:
        if not self._shown:
            return
        self._sync_geometry()
        if rect == self._frame_rect and self._vs == self._frame_vs:
            return
        self._frame_rect = rect
        self._frame_vs = self._vs
        self.canvas.delete("frame")
        if rect is None or self._vs is None:
            return
        x1 = rect.left - self._vs.left
        y1 = rect.top - self._vs.top
        x2 = rect.right - self._vs.left
        y2 = rect.bottom - self._vs.top
        # Thin dashed light-blue frame (magenta key is fully transparent elsewhere).
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="#9FD4F0",
            width=2,
            dash=(5, 4),
            tags="frame",
        )

    def set_markers(self, points: list[tuple[int, int]], draggable: bool) -> None:
        if not draggable or not points:
            self.clear_markers()
            return
        if len(points) != len(self._markers):
            self.clear_markers()
            for index in range(len(points)):
                self._markers.append(Marker(self.root, index, self._on_moved, self._on_released))
        for marker, (x, y) in zip(self._markers, points):
            marker.show_at(x, y)

    def clear_markers(self) -> None:
        for marker in self._markers:
            marker.destroy()
        self._markers = []

    def _sync_geometry(self) -> None:
        screen = win32_api.virtual_screen()
        if screen == self._vs:
            return
        self._vs = screen
        self.win.geometry(f"{screen.width}x{screen.height}+{screen.left}+{screen.top}")

    def _apply_styles(self) -> None:
        hwnd = win32_api.widget_hwnd(self.win)
        win32_api.add_exstyle(hwnd, win32_api.OVERLAY_EXSTYLE)
        win32_api.raise_topmost(hwnd)
