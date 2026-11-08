"""Preset records and window-relative coordinate math."""

from __future__ import annotations

from dataclasses import dataclass, field


TIMING_MODES = ("instantaneous", "one_second", "realtime")


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def normalized_to_screen(rect: Rect, nx: float, ny: float) -> tuple[int, int]:
    """Map fractions onto the last pixel inside a window rect.

    ``GetWindowRect`` is exclusive of its right and bottom edges, so ``nx``
    and ``ny`` of 1 land on the last pixel that still belongs to the window.
    """

    span_x = max(rect.width - 1, 0)
    span_y = max(rect.height - 1, 0)
    x = int(round(rect.left + float(nx) * span_x))
    y = int(round(rect.top + float(ny) * span_y))
    return x, y


def screen_to_normalized(rect: Rect, x: int, y: int) -> tuple[float, float]:
    span_x = max(rect.width - 1, 0)
    span_y = max(rect.height - 1, 0)
    if span_x == 0 or span_y == 0:
        return 0.0, 0.0
    return (x - rect.left) / span_x, (y - rect.top) / span_y


def timing_for_point(mode: str, *, gap_ms: int, held_ms: int) -> tuple[int, int]:
    """Return ``(delay_ms, hold_ms)`` for one recorded point."""

    if mode == "instantaneous":
        return 50, 50
    if mode == "one_second":
        return 950, 50
    if mode == "realtime":
        return max(0, int(gap_ms)), max(50, int(held_ms))
    raise ValueError(f"unknown timing mode: {mode}")


@dataclass
class ClickPoint:
    nx: float
    ny: float
    delay_ms: int
    hold_ms: int
    button: str = "left"
    label: str = ""


@dataclass
class Preset:
    name: str
    timing_mode: str
    points: list[ClickPoint] = field(default_factory=list)
    loop: bool = True
    loop_count: int | None = None
    notes: str = ""
    version: int = 1
    path: str | None = None


@dataclass
class Settings:
    click_method: str = "foreground"
    focus_before_run: bool = True
    restore_cursor: bool = True
    countdown_seconds: int = 0
    humanize_level: str = "off"
    lab_mode: str = "auto"  # auto | supervised
    trace_level: str = "failure"  # off | failure | all
    # Flight deck: expand VK (default backtick), optional per-anchor title overrides, geometry.
    flight_deck_expand_vk: int = 0xC0  # VK_OEM_3
    flight_deck_expand_by_anchor: dict[str, int] = field(default_factory=dict)
    flight_deck_geometry: str | None = None
    flight_deck_user_hidden: bool = False
    # Last successful anchor title (HWND does not survive restart).
    last_anchor_title: str | None = None


class ClickError(RuntimeError):
    """A click could not be delivered."""
