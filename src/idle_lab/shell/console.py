"""Shared console buffer — Molecule Lab dock + Deck float both read this."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Literal

Level = Literal["ok", "warn", "error", "run", "info"]


@dataclass(frozen=True)
class ConsoleLine:
    message: str
    level: Level


class SharedConsole:
    """Ring buffer + fan-out. No Tk — UI panels subscribe and render."""

    def __init__(self, *, maxlen: int = 400) -> None:
        self._lines: Deque[ConsoleLine] = deque(maxlen=max(50, int(maxlen)))
        self._listeners: list[Callable[[ConsoleLine], None]] = []

    def clear(self) -> None:
        self._lines.clear()

    def lines(self) -> tuple[ConsoleLine, ...]:
        return tuple(self._lines)

    def subscribe(self, listener: Callable[[ConsoleLine], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[ConsoleLine], None]) -> None:
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def append(self, message: str, level: str = "info") -> None:
        text = str(message or "").strip()
        if not text:
            return
        norm: Level = level if level in {"ok", "warn", "error", "run", "info"} else "info"
        line = ConsoleLine(message=text, level=norm)
        self._lines.append(line)
        for listener in list(self._listeners):
            try:
                listener(line)
            except Exception:
                pass
