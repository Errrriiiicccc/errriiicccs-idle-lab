"""Mouse-wheel / drag scrolling helpers and in-session scroll persistence.

Scroll positions are remembered in memory for the life of the process. Leaving a
tab (or rebuilding a list) restores the last offset until the program restarts.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk


def _canvas_of(frame: ctk.CTkScrollableFrame):
    return frame._parent_canvas  # noqa: SLF001 — CTk has no public yview API


def get_yview(frame: ctk.CTkScrollableFrame) -> tuple[float, float]:
    try:
        return tuple(float(v) for v in _canvas_of(frame).yview())  # type: ignore[return-value]
    except Exception:
        return (0.0, 1.0)


def set_yview(frame: ctk.CTkScrollableFrame, top: float) -> None:
    top = max(0.0, min(1.0, float(top)))
    try:
        canvas = _canvas_of(frame)
        canvas.update_idletasks()
        canvas.yview_moveto(top)
    except Exception:
        pass


def enable_drag_scroll(frame: ctk.CTkScrollableFrame) -> None:
    """Middle-button drag anywhere on the frame; left-drag on the canvas chrome.

    Wheel scrolling is already provided by CustomTkinter. This adds click-drag
    so long menus can be scrubbed without using the thin scrollbar thumb.
    """

    if getattr(frame, "_idle_lab_drag_scroll", False):
        return
    frame._idle_lab_drag_scroll = True  # type: ignore[attr-defined]

    canvas = _canvas_of(frame)
    state: dict[str, Any] = {"y": None, "active": False}

    def press(event) -> None:
        state["y"] = event.y_root
        state["active"] = True

    def motion(event) -> str | None:
        if not state["active"] or state["y"] is None:
            return None
        dy = int(state["y"] - event.y_root)
        if dy == 0:
            return "break"
        state["y"] = event.y_root
        try:
            canvas.yview_scroll(dy, "units")
        except Exception:
            pass
        return "break"

    def release(_event) -> None:
        state["y"] = None
        state["active"] = False

    # Middle mouse — works over buttons/labels without stealing their clicks.
    for widget in (canvas, frame):
        widget.bind("<ButtonPress-2>", press, add="+")
        widget.bind("<B2-Motion>", motion, add="+")
        widget.bind("<ButtonRelease-2>", release, add="+")

    # Left drag on the canvas gutter / empty inner frame.
    canvas.bind("<ButtonPress-1>", press, add="+")
    canvas.bind("<B1-Motion>", motion, add="+")
    canvas.bind("<ButtonRelease-1>", release, add="+")
    frame.bind("<ButtonPress-1>", press, add="+")
    frame.bind("<B1-Motion>", motion, add="+")
    frame.bind("<ButtonRelease-1>", release, add="+")


class ScrollMemory:
    """In-memory scroll tops keyed by stable ids (tab + widget role)."""

    def __init__(self) -> None:
        self._tops: dict[str, float] = {}
        self._frames: dict[str, ctk.CTkScrollableFrame] = {}

    def register(self, key: str, frame: ctk.CTkScrollableFrame, *, drag: bool = True) -> None:
        self._frames[key] = frame
        if drag:
            enable_drag_scroll(frame)
        if key in self._tops:
            # Defer until geometry is ready.
            frame.after(1, lambda k=key: self.restore(k))

    def remember(self, key: str) -> None:
        frame = self._frames.get(key)
        if frame is None:
            return
        try:
            if not frame.winfo_exists():
                return
        except Exception:
            return
        top, _ = get_yview(frame)
        self._tops[key] = top

    def restore(self, key: str) -> None:
        frame = self._frames.get(key)
        if frame is None or key not in self._tops:
            return
        try:
            if not frame.winfo_exists():
                return
        except Exception:
            return
        set_yview(frame, self._tops[key])

    def remember_prefix(self, prefix: str) -> None:
        for key in list(self._frames):
            if key.startswith(prefix):
                self.remember(key)

    def restore_prefix(self, prefix: str) -> None:
        for key in list(self._frames):
            if key.startswith(prefix):
                self.restore(key)

    def around_rebuild(self, key: str, rebuild_fn) -> None:
        """Save scroll, run a list rebuild that destroys children, then restore."""

        self.remember(key)
        rebuild_fn()
        frame = self._frames.get(key)
        if frame is not None:
            frame.after(1, lambda k=key: self.restore(k))
        else:
            self.restore(key)
