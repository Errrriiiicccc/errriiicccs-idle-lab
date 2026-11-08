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


def foreground_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    *,
    restore_cursor: bool,
    steps: int = 10,
    step_ms: int = 25,
    hold_end_ms: int = 350,
    stop: threading.Event | None = None,
) -> None:
    """Press → slow drag → hold still → release.

    Holding at the end before release kills Android/BlueStacks fling momentum
    that a wheel flick or fast swipe would cause.
    """

    saved_x, saved_y = win32_api.cursor_pos()
    released = False
    move_steps = max(2, int(steps))
    try:
        win32_api.set_cursor_pos(start_x, start_y)
        _sleep_ms(20, stop)
        win32_api.send_left_button(True)
        _sleep_ms(30, stop)
        for index in range(1, move_steps + 1):
            if stop is not None and stop.is_set():
                break
            t = index / move_steps
            x = int(round(start_x + (end_x - start_x) * t))
            y = int(round(start_y + (end_y - start_y) * t))
            win32_api.set_cursor_pos(x, y)
            _sleep_ms(max(1, step_ms), stop)
        # Optional end hold: long hold kills fling momentum; 0 = release while moving.
        win32_api.set_cursor_pos(end_x, end_y)
        hold = max(0, int(hold_end_ms))
        if hold:
            _sleep_ms(hold, stop)
        win32_api.send_left_button(False)
        released = True
        _sleep_ms(30, None)
    finally:
        if not released:
            win32_api.send_left_button(False)
        if restore_cursor:
            win32_api.set_cursor_pos(saved_x, saved_y)
