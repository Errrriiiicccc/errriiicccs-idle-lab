"""Pick a top-level window by title (exact match) for deck-first re-anchor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowCandidate:
    hwnd: int
    title: str
    pid: int
    visible: bool
    minimized: bool


def pick_window_by_title(
    candidates: list[WindowCandidate] | tuple[WindowCandidate, ...],
    title: str,
    *,
    our_pid: int,
) -> int | None:
    """Return hwnd for an exact title match, or None if missing/ambiguous.

    Prefers visible, non-minimized windows. Skips ``our_pid``. If more than one
    candidate shares the best quality tier, returns None (operator picks with A).
    """

    needle = (title or "").strip()
    if not needle:
        return None
    matches = [
        c
        for c in candidates
        if c.hwnd
        and c.pid != int(our_pid)
        and (c.title or "").strip() == needle
    ]
    if not matches:
        return None

    def rank(c: WindowCandidate) -> tuple[int, int]:
        # Lower is better: visible+restored, then visible+minimized, then hidden.
        if c.visible and not c.minimized:
            return (0, c.hwnd)
        if c.visible:
            return (1, c.hwnd)
        return (2, c.hwnd)

    matches.sort(key=rank)
    best = rank(matches[0])[0]
    top = [c for c in matches if rank(c)[0] == best]
    if len(top) != 1:
        return None
    return int(top[0].hwnd)
