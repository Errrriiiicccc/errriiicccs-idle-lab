"""Exclusive Idle Lab ↔ Flight Deck surface rules (pure logic)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SurfaceKind(str, Enum):
    IDLE_LAB = "idle_lab"
    FLIGHT_DECK = "flight_deck"


@dataclass(frozen=True)
class Surface:
    """Which operator surface should own the screen."""

    kind: SurfaceKind

    @property
    def idle_lab_visible(self) -> bool:
        return self.kind is SurfaceKind.IDLE_LAB

    @property
    def flight_deck_visible(self) -> bool:
        return self.kind is SurfaceKind.FLIGHT_DECK


def can_show_idle_lab(*, anything_running: bool) -> bool:
    """Hard rule: anything running → Idle Lab closed; Flight Deck only."""

    return not bool(anything_running)


def hotkeys_allowed(*, surface: SurfaceKind | Surface | str, anything_running: bool = False) -> bool:
    """Idle Lab open → no keyboard hotkeys. Deck (or run-forced Deck) may listen."""

    _ = anything_running
    kind = _as_kind(surface)
    return kind is SurfaceKind.FLIGHT_DECK


def ensure_exclusive(
    *,
    want: SurfaceKind | Surface | str,
    anything_running: bool,
) -> Surface:
    """Resolve the requested surface against run → Deck-only."""

    kind = _as_kind(want)
    if anything_running:
        return Surface(SurfaceKind.FLIGHT_DECK)
    return Surface(kind)


def _as_kind(value: SurfaceKind | Surface | str) -> SurfaceKind:
    if isinstance(value, Surface):
        return value.kind
    if isinstance(value, SurfaceKind):
        return value
    return SurfaceKind(str(value))
