"""Synchronous preset playback for the automations worker thread."""

from __future__ import annotations

import time

from idle_lab.humanize import HumanizeProfile, human_click, human_wait
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
    humanize: HumanizeProfile | None = None,
) -> None:
    profile = humanize or HumanizeProfile.from_level("medium")
    if focus and hwnd:
        win32_api.focus_window(hwnd)
        time.sleep(0.05)
    for point in points:
        if point.delay_ms:
            human_wait(point.delay_ms, profile)
        x, y = normalized_to_screen(rect, point.nx, point.ny)
        human_click(
            x,
            y,
            point.hold_ms,
            method=method,
            hwnd=hwnd,
            restore_cursor=restore_cursor,
            profile=profile,
            rect=rect,
        )
