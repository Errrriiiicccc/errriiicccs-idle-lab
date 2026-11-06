"""Operator mode: auto vs supervised, plus activity status helpers."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable


LAB_MODES = ("auto", "supervised")


def normalize_lab_mode(value: str | None) -> str:
    key = str(value or "auto").strip().lower()
    return key if key in LAB_MODES else "auto"


@dataclass
class OperatorStatus:
    """Published snapshot for Activity / mode chip."""

    mode: str = "auto"  # auto | supervised
    phase: str = "idle"  # idle | running | blocked | unanchored
    detail: str = ""
    blocking_id: str | None = None
    deferred_summary: str = ""


@dataclass
class SuperviseGate:
    """UI thread answers confirm requests from worker threads."""

    ask: Callable[[str], bool] | None = None
    enabled: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def request(self, description: str, *, stop: threading.Event | None = None) -> bool:
        if not self.enabled or self.ask is None:
            return True
        if stop is not None and stop.is_set():
            return False
        with self._lock:
            return bool(self.ask(description))


def humanize_level_tooltip(level: str) -> str:
    """Plain-language summary of humanize levels for UI tooltips."""

    key = str(level or "medium").strip().lower()
    tips = {
        "off": "Exact aim and timing — no jitter, no cursor travel.",
        "light": "~2px aim jitter, ~12% delay/hold variance, short cursor travel.",
        "medium": "~5px aim jitter, ~22% delay variance, eased multi-step travel (default).",
        "heavy": "~9px aim jitter, ~35% delay variance, longer travel — slower ticks.",
    }
    return tips.get(key, tips["medium"])
