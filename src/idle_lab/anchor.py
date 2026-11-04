"""Track the top-level window the presets are attached to."""

from __future__ import annotations

import os
import threading

from idle_lab.models import Rect
from idle_lab import win32_api


class Anchor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.hwnd = 0
        self.title = ""
        self.rect: Rect | None = None

    def capture(self, hwnd: int) -> str | None:
        if not hwnd or not win32_api.is_window(hwnd):
            return "That click did not land on a window."
        title = win32_api.get_window_text(hwnd) or "(untitled)"
        if win32_api.pid_of(hwnd) == os.getpid() and title != "Click logger":
            return "Pick the emulator, not this autoclicker."
        rect = win32_api.get_window_rect(hwnd)
        if rect is None or rect.width < 20 or rect.height < 20:
            return "That window is too small to anchor."
        with self._lock:
            self.hwnd = int(hwnd)
            self.title = title
            self.rect = rect
        return None

    def clear(self) -> None:
        with self._lock:
            self.hwnd = 0
            self.title = ""
            self.rect = None

    def snapshot(self) -> tuple[str, int, Rect | None, str]:
        """Return status, hwnd, rect, and title.

        Status is ``missing``, ``closed``, ``minimized``, or ``ok``.
        """

        with self._lock:
            hwnd = self.hwnd
        if not hwnd:
            return "missing", 0, None, ""
        if not win32_api.is_window(hwnd):
            return "closed", hwnd, None, ""
        title = win32_api.get_window_text(hwnd) or "(untitled)"
        rect = win32_api.get_window_rect(hwnd)
        if win32_api.is_iconic(hwnd):
            return "minimized", hwnd, rect, title
        if rect is None:
            return "closed", hwnd, None, title
        with self._lock:
            self.title = title
            self.rect = rect
        return "ok", hwnd, rect, title
