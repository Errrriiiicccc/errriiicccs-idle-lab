"""Post a click into the anchored window without moving the cursor."""

from __future__ import annotations

import threading
import time

from idle_lab.models import ClickError
from idle_lab import win32_api


def background_click(
    anchor_hwnd: int,
    x: int,
    y: int,
    hold_ms: int,
    stop: threading.Event | None = None,
) -> None:
    if not win32_api.is_window(anchor_hwnd):
        raise ClickError("The anchored window is gone.")
    target, client_x, client_y = win32_api.child_at_screen_point(anchor_hwnd, x, y)
    if not target:
        raise ClickError("No child window was found under that point.")
    win32_api.post_left_click(target, client_x, client_y, down=True)
    remaining = max(1, hold_ms) / 1000
    while remaining > 0:
        if stop is not None and stop.is_set():
            break
        step = min(0.02, remaining)
        time.sleep(step)
        remaining -= step
    win32_api.post_left_click(target, client_x, client_y, down=False)
