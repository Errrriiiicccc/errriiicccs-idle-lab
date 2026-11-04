"""Capture points from the Space key."""

from __future__ import annotations

import time
from collections.abc import Callable

from idle_lab.models import ClickPoint, Rect, screen_to_normalized, timing_for_point


class Recorder:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.perf_counter
        self.active = False
        self.name = ""
        self.mode = ""
        self.points: list[ClickPoint] = []
        self.last_error = ""
        self._last_release = 0.0
        self._down_at: float | None = None
        self._down_pos: tuple[int, int] | None = None

    def start(self, name: str, mode: str) -> None:
        now = self._clock()
        self.active = True
        self.name = name
        self.mode = mode
        self.points = []
        self.last_error = ""
        self._last_release = now
        self._down_at = None
        self._down_pos = None

    def space_down(self, x: int, y: int) -> None:
        if not self.active or self._down_at is not None:
            return
        self._down_at = self._clock()
        self._down_pos = (int(x), int(y))

    def space_up(self, rect_provider: Callable[[], Rect | None]) -> ClickPoint | None:
        if not self.active or self._down_at is None or self._down_pos is None:
            return None
        now = self._clock()
        gap_ms = int((self._down_at - self._last_release) * 1000)
        held_ms = int((now - self._down_at) * 1000)
        delay_ms, hold_ms = timing_for_point(self.mode, gap_ms=gap_ms, held_ms=held_ms)
        self._last_release = now
        self._down_at = None
        rect = rect_provider()
        if rect is None or rect.width <= 1 or rect.height <= 1:
            self.last_error = "The anchored window is not available, so that point was skipped."
            self._down_pos = None
            return None
        nx, ny = screen_to_normalized(rect, self._down_pos[0], self._down_pos[1])
        self._down_pos = None
        self.last_error = ""
        point = ClickPoint(nx=nx, ny=ny, delay_ms=delay_ms, hold_ms=hold_ms, button="left", label="")
        self.points.append(point)
        return point

    def finish(self) -> list[ClickPoint]:
        self.active = False
        self._down_at = None
        self._down_pos = None
        return list(self.points)
