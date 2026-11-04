"""Real cursor clicks. These are the ones an emulator usually accepts."""

from __future__ import annotations

import threading
import time

from idle_lab import win32_api


def _sleep_ms(duration_ms: int, stop: threading.Event | None) -> bool:
    remaining = max(0, duration_ms) / 1000
    while remaining > 0:
        if stop is not None and stop.is_set():
            return False
        step = min(0.02, remaining)
        time.sleep(step)
        remaining -= step
    return True


def foreground_click(
    x: int,
    y: int,
    hold_ms: int,
    restore_cursor: bool,
    stop: threading.Event | None = None,
) -> None:
    saved_x, saved_y = win32_api.cursor_pos()
    released = False
    try:
        win32_api.set_cursor_pos(x, y)
        _sleep_ms(15, stop)
        win32_api.send_left_button(True)
        _sleep_ms(max(1, hold_ms), stop)
        win32_api.send_left_button(False)
        released = True
        _sleep_ms(20, None)
    finally:
        if not released:
            win32_api.send_left_button(False)
        if restore_cursor:
            win32_api.set_cursor_pos(saved_x, saved_y)
