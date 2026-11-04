"""Synchronous preset playback for the automations worker thread."""

from __future__ import annotations

import time

from idle_lab.click_background import background_click
from idle_lab.click_foreground import foreground_click
from idle_lab.models import ClickPoint, Rect, normalized_to_screen
from idle_lab import win32_api


def play_points_sync(
    points: list[ClickPoint],
    rect: Rect,
    *,
    method: str,
    hwnd: int,
    focus: bool,
    restore_cursor: bool,
) -> None:
    if focus and hwnd:
        win32_api.focus_window(hwnd)
        time.sleep(0.05)
    for point in points:
        if point.delay_ms:
            time.sleep(max(point.delay_ms, 0) / 1000.0)
        x, y = normalized_to_screen(rect, point.nx, point.ny)
        if method == "background":
            background_click(hwnd, x, y, point.hold_ms)
        else:
            foreground_click(x, y, point.hold_ms, restore_cursor)
