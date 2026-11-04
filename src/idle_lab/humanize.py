"""Human-like timing and aim applied at click/scroll execution time.

Intent (preset points, AI-batch steps) stays exact. This module turns those
intents into slightly imperfect actions: pixel jitter, delay/hold variance,
and optional cursor travel for foreground clicks.

Not stealth — ordinary input with less robotic pacing.
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass

from idle_lab.click_background import background_click
from idle_lab.click_foreground import foreground_click
from idle_lab.models import Rect
from idle_lab import win32_api


HUMANIZE_LEVELS = ("off", "light", "medium", "heavy")

# level → (pos_jitter_px, delay_jitter_frac, hold_jitter_frac, pre_pause_ms_range,
#          move_steps_range, move_step_ms_range, scroll_gap_ms_range)
_LEVEL_PARAMS: dict[str, tuple] = {
    "off": (0, 0.0, 0.0, (0, 0), (0, 0), (0, 0), (40, 40)),
    "light": (2, 0.12, 0.12, (0, 25), (4, 7), (8, 14), (35, 70)),
    "medium": (5, 0.22, 0.20, (15, 55), (6, 11), (10, 18), (45, 110)),
    "heavy": (9, 0.35, 0.30, (30, 90), (9, 16), (12, 22), (60, 160)),
}


def normalize_level(value: str | None) -> str:
    key = str(value or "medium").strip().lower()
    return key if key in _LEVEL_PARAMS else "medium"


@dataclass(frozen=True)
class HumanizeProfile:
    level: str = "medium"

    @classmethod
    def from_level(cls, level: str | None) -> HumanizeProfile:
        return cls(level=normalize_level(level))

    @property
    def enabled(self) -> bool:
        return self.level != "off"

    def _params(self) -> tuple:
        return _LEVEL_PARAMS[normalize_level(self.level)]


@dataclass(frozen=True)
class ResolvedClick:
    x: int
    y: int
    hold_ms: int
    pre_pause_ms: int
    move_steps: int
    move_step_ms: int


def _rng(rng: random.Random | None) -> random.Random:
    return rng if rng is not None else random.Random()


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def jitter_delay_ms(nominal_ms: int, profile: HumanizeProfile, *, rng: random.Random | None = None) -> int:
    """Vary a wait that sits between actions."""

    nominal = max(0, int(nominal_ms))
    if not profile.enabled or nominal == 0:
        return nominal
    _pos, delay_frac, _hold, *_rest = profile._params()
    roll = _rng(rng).uniform(-delay_frac, delay_frac)
    return max(0, int(round(nominal * (1.0 + roll))))


def jitter_hold_ms(nominal_ms: int, profile: HumanizeProfile, *, rng: random.Random | None = None) -> int:
    nominal = max(1, int(nominal_ms))
    if not profile.enabled:
        return nominal
    _pos, _delay, hold_frac, *_rest = profile._params()
    roll = _rng(rng).uniform(-hold_frac, hold_frac)
    return max(1, int(round(nominal * (1.0 + roll))))


def jitter_point(
    x: int,
    y: int,
    profile: HumanizeProfile,
    *,
    rect: Rect | None = None,
    rng: random.Random | None = None,
) -> tuple[int, int]:
    """Offset a screen point; keep it inside the anchor rect when known."""

    if not profile.enabled:
        return int(x), int(y)
    pos_jitter, *_rest = profile._params()
    if pos_jitter <= 0:
        return int(x), int(y)
    dice = _rng(rng)
    # Slight bias toward the center of a disc rather than a square.
    angle = dice.uniform(0, 2 * math.pi)
    radius = dice.uniform(0, float(pos_jitter))
    jx = int(round(x + radius * math.cos(angle)))
    jy = int(round(y + radius * math.sin(angle)))
    if rect is not None:
        jx = _clamp_int(jx, rect.left, rect.right - 1)
        jy = _clamp_int(jy, rect.top, rect.bottom - 1)
    return jx, jy


def resolve_click(
    x: int,
    y: int,
    hold_ms: int,
    profile: HumanizeProfile,
    *,
    rect: Rect | None = None,
    rng: random.Random | None = None,
) -> ResolvedClick:
    dice = _rng(rng)
    jx, jy = jitter_point(x, y, profile, rect=rect, rng=dice)
    hold = jitter_hold_ms(hold_ms, profile, rng=dice)
    if not profile.enabled:
        return ResolvedClick(x=jx, y=jy, hold_ms=hold, pre_pause_ms=0, move_steps=0, move_step_ms=0)
    _pos, _d, _h, pre_range, steps_range, step_ms_range, _scroll = profile._params()
    pre = dice.randint(int(pre_range[0]), int(pre_range[1])) if pre_range[1] > 0 else 0
    steps = dice.randint(int(steps_range[0]), int(steps_range[1])) if steps_range[1] > 0 else 0
    step_ms = dice.randint(int(step_ms_range[0]), int(step_ms_range[1])) if step_ms_range[1] > 0 else 0
    return ResolvedClick(
        x=jx,
        y=jy,
        hold_ms=hold,
        pre_pause_ms=pre,
        move_steps=steps,
        move_step_ms=step_ms,
    )


def interruptible_sleep(duration_ms: int, stop: threading.Event | None = None) -> bool:
    """Sleep that can be cancelled. Returns False if stopped."""

    remaining = max(0, int(duration_ms)) / 1000
    while remaining > 0:
        if stop is not None and stop.is_set():
            return False
        step = min(0.02, remaining)
        time.sleep(step)
        remaining -= step
    return True


def human_wait(
    nominal_ms: int,
    profile: HumanizeProfile,
    *,
    stop: threading.Event | None = None,
    rng: random.Random | None = None,
) -> bool:
    return interruptible_sleep(jitter_delay_ms(nominal_ms, profile, rng=rng), stop)


def _ease_out_quad(t: float) -> float:
    return 1.0 - (1.0 - t) * (1.0 - t)


def _move_cursor_human(
    target_x: int,
    target_y: int,
    *,
    steps: int,
    step_ms: int,
    stop: threading.Event | None,
    rng: random.Random,
) -> bool:
    """Travel from the current cursor toward the target with light path noise."""

    if steps <= 0:
        win32_api.set_cursor_pos(target_x, target_y)
        return True
    start_x, start_y = win32_api.cursor_pos()
    dx = target_x - start_x
    dy = target_y - start_y
    distance = math.hypot(dx, dy)
    if distance < 3:
        win32_api.set_cursor_pos(target_x, target_y)
        return True
    # Tiny perpendicular wobble so the path isn't a perfect line.
    if distance > 0:
        nx = -dy / distance
        ny = dx / distance
    else:
        nx = ny = 0.0
    wobble = min(4.0, distance * 0.04)
    for index in range(1, steps + 1):
        if stop is not None and stop.is_set():
            return False
        t = _ease_out_quad(index / steps)
        along_x = start_x + dx * t
        along_y = start_y + dy * t
        # Peak wobble mid-path, settle on the last step.
        side = math.sin(math.pi * t) * wobble * rng.uniform(-1.0, 1.0)
        x = int(round(along_x + nx * side))
        y = int(round(along_y + ny * side))
        if index == steps:
            x, y = target_x, target_y
        win32_api.set_cursor_pos(x, y)
        if not interruptible_sleep(max(1, step_ms + rng.randint(-2, 3)), stop):
            return False
    return True


def human_click(
    x: int,
    y: int,
    hold_ms: int,
    *,
    method: str,
    hwnd: int,
    restore_cursor: bool,
    profile: HumanizeProfile,
    rect: Rect | None = None,
    stop: threading.Event | None = None,
    rng: random.Random | None = None,
) -> None:
    """Deliver one click with profile-based humanization."""

    dice = _rng(rng)
    resolved = resolve_click(x, y, hold_ms, profile, rect=rect, rng=dice)
    if method == "background":
        if resolved.pre_pause_ms and not interruptible_sleep(resolved.pre_pause_ms, stop):
            return
        background_click(hwnd, resolved.x, resolved.y, resolved.hold_ms, stop)
        return

    # Foreground: optional hesitation + path, then reuse the low-level click
    # without a second teleport jump by parking the cursor first.
    saved_x, saved_y = win32_api.cursor_pos()
    try:
        if resolved.pre_pause_ms and not interruptible_sleep(resolved.pre_pause_ms, stop):
            return
        if profile.enabled and resolved.move_steps > 0:
            if not _move_cursor_human(
                resolved.x,
                resolved.y,
                steps=resolved.move_steps,
                step_ms=resolved.move_step_ms,
                stop=stop,
                rng=dice,
            ):
                return
            # Cursor is already on target — hold + click without another teleport.
            win32_api.send_left_button(True)
            if not interruptible_sleep(resolved.hold_ms, stop):
                win32_api.send_left_button(False)
                return
            win32_api.send_left_button(False)
            interruptible_sleep(20, None)
        else:
            foreground_click(resolved.x, resolved.y, resolved.hold_ms, False, stop)
    finally:
        if restore_cursor:
            win32_api.set_cursor_pos(saved_x, saved_y)


def human_scroll_gap_ms(profile: HumanizeProfile, *, rng: random.Random | None = None) -> int:
    _a, _b, _c, _d, _e, _f, gap_range = profile._params()
    low, high = int(gap_range[0]), int(gap_range[1])
    if high <= low:
        return low
    return _rng(rng).randint(low, high)
