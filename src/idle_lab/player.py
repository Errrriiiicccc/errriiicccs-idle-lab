"""Play a preset against the current anchored rectangle."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable

from idle_lab.click_background import background_click
from idle_lab.click_foreground import foreground_click
from idle_lab.models import ClickError, ClickPoint, Rect, normalized_to_screen
from idle_lab import win32_api


class Player:
    def __init__(self) -> None:
        self.events: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._thread: threading.Thread | None = None
        self.paused = False

    @property
    def is_active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        points: list[ClickPoint],
        *,
        loop: bool,
        loop_count: int | None,
        method: str,
        focus: bool,
        restore_cursor: bool,
        countdown: int,
        hwnd: int,
        snapshot: Callable[[], tuple[str, int, Rect | None, str]],
    ) -> None:
        if self.is_active:
            return
        self._stop.clear()
        self._pause.clear()
        self.paused = False
        points = [
            ClickPoint(point.nx, point.ny, point.delay_ms, point.hold_ms, point.button, point.label)
            for point in points
        ]
        self._thread = threading.Thread(
            target=self._run,
            name="click-player",
            daemon=True,
            kwargs={
                "points": list(points),
                "loop": loop,
                "loop_count": loop_count,
                "method": method,
                "focus": focus,
                "restore_cursor": restore_cursor,
                "countdown": countdown,
                "hwnd": hwnd,
                "snapshot": snapshot,
            },
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._pause.clear()

    def stop_and_wait(self) -> None:
        self.stop()
        if self._thread is not None:
            self._thread.join(1.5)

    def toggle_pause(self) -> None:
        if not self.is_active:
            return
        self.paused = not self.paused
        if self.paused:
            self._pause.set()
        else:
            self._pause.clear()
        self.events.put(("paused", self.paused))

    def _wait(self, duration_ms: int) -> bool:
        remaining = max(0, duration_ms) / 1000
        while remaining > 0:
            if self._stop.is_set():
                return False
            if self._pause.is_set():
                time.sleep(0.05)
                continue
            step = min(0.02, remaining)
            time.sleep(step)
            remaining -= step
        return not self._stop.is_set()

    def _run(self, **kwargs) -> None:
        try:
            reason = self._loop(**kwargs)
        except ClickError as exc:
            reason = str(exc)
        except Exception as exc:
            reason = f"Playback failed: {exc}"
        self.paused = False
        self.events.put(("stopped", reason))

    def _loop(
        self,
        points: list[ClickPoint],
        loop: bool,
        loop_count: int | None,
        method: str,
        focus: bool,
        restore_cursor: bool,
        countdown: int,
        hwnd: int,
        snapshot: Callable[[], tuple[str, int, Rect | None, str]],
    ) -> str:
        if countdown:
            self.events.put(("status", f"Starting in {countdown}s.", "warn"))
            if not self._wait(countdown * 1000):
                return "Stopped."
        if method == "foreground" and focus:
            if not win32_api.focus_window(hwnd):
                self.events.put(("status", "Could not focus the window. Clicks still move the cursor.", "warn"))
        repeats = 1 if not loop else loop_count
        loop_index = 0
        while True:
            loop_index += 1
            for index, point in enumerate(points):
                self.events.put(("point", index, loop_index, len(points)))
                if not self._wait(point.delay_ms):
                    return "Stopped."
                status, current_hwnd, rect, _title = snapshot()
                if status == "minimized":
                    return "The anchored window was minimized, so playback stopped."
                if status != "ok" or rect is None or not current_hwnd:
                    return "The anchored window is gone, so playback stopped."
                x, y = normalized_to_screen(rect, point.nx, point.ny)
                if method == "background":
                    background_click(current_hwnd, x, y, point.hold_ms, self._stop)
                else:
                    foreground_click(x, y, point.hold_ms, restore_cursor, self._stop)
                if self._stop.is_set():
                    return "Stopped."
            if repeats is not None and loop_index >= repeats:
                return "Finished."
