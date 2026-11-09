"""LCO session console — buffered log flushed to a run folder on pause/exit."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

CONSOLE_VERBOSITY = ("events", "results", "process")
DEFAULT_VERBOSITY = "results"


def normalize_verbosity(value: str | None) -> str:
    name = str(value or DEFAULT_VERBOSITY).strip().lower()
    return name if name in CONSOLE_VERBOSITY else DEFAULT_VERBOSITY


def next_verbosity(value: str | None) -> str:
    current = normalize_verbosity(value)
    idx = CONSOLE_VERBOSITY.index(current)
    return CONSOLE_VERBOSITY[(idx + 1) % len(CONSOLE_VERBOSITY)]


_LEVEL_RANK = {"events": 1, "results": 2, "process": 3, "comment": 1}


@dataclass(frozen=True)
class ConsoleLine:
    stamp: str
    level: str
    message: str

    def dump_text(self) -> str:
        """Always includes the timestamp (written to console.log)."""

        return f"{self.stamp} [{self.level}] {self.message}"

    def display_text(self, *, show_timestamps: bool) -> str:
        if show_timestamps:
            return self.dump_text()
        return f"[{self.level}] {self.message}"


@dataclass
class ConsoleSession:
    """One LCO run's console. Lines buffer in memory and flush to disk on pause/exit."""

    project_root: Path
    enabled: bool = False
    verbosity: str = DEFAULT_VERBOSITY
    folder: Path | None = None
    lines: list[ConsoleLine] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _dirty: bool = False
    on_change: Callable[[], None] | None = None

    def configure(self, *, enabled: bool, verbosity: str) -> None:
        with self._lock:
            self.enabled = bool(enabled)
            self.verbosity = normalize_verbosity(verbosity)

    def start_run(self) -> Path | None:
        """Create a run folder when console is enabled at LCO enter."""

        with self._lock:
            self.lines.clear()
            self._dirty = False
            self.folder = None
            if not self.enabled:
                self._notify()
                return None
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            folder = Path(self.project_root) / "runs" / f"lco-console-{stamp}"
            folder.mkdir(parents=True, exist_ok=True)
            self.folder = folder
            self._append_unlocked(
                "events",
                f"console start · verbosity={self.verbosity} · folder={folder.name}",
            )
            self._flush_unlocked()
            self._notify()
            return folder

    def stop_run(self, *, reason: str = "exit") -> Path | None:
        with self._lock:
            if self.folder is None:
                return None
            self._append_unlocked("events", f"console stop · reason={reason}")
            path = self._flush_unlocked()
            self._notify()
            return path

    def flush(self, *, reason: str = "flush") -> Path | None:
        with self._lock:
            if self.folder is None:
                return None
            if reason != "flush":
                self._append_unlocked("events", f"console flush · reason={reason}")
            path = self._flush_unlocked()
            self._notify()
            return path

    def event(self, message: str) -> None:
        self._append("events", message)

    def result(self, message: str) -> None:
        self._append("results", message)

    def process(self, message: str) -> None:
        self._append("process", message)

    def user_comment(self, text: str) -> bool:
        """Append a user comment. Returns False if console is off or text empty."""

        body = str(text or "").strip()
        if not body:
            return False
        with self._lock:
            if not self.enabled:
                return False
            self._ensure_folder_unlocked()
            self._append_unlocked("comment", f"User Comment: {body}", force=True)
            self._flush_unlocked()
            self._notify()
            return True

    def set_enabled(self, enabled: bool) -> bool:
        with self._lock:
            want = bool(enabled)
            if want and not self.enabled:
                self.enabled = True
                self._ensure_folder_unlocked()
                self._append_unlocked(
                    "events",
                    f"console enabled · verbosity={self.verbosity} · folder={self.folder.name if self.folder else '?'}",
                )
                self._flush_unlocked()
            elif not want and self.enabled:
                self._append_unlocked("events", "console disabled")
                self._flush_unlocked()
                self.enabled = False
            self._notify()
            return self.enabled

    def cycle_verbosity(self) -> str:
        with self._lock:
            self.verbosity = next_verbosity(self.verbosity)
            if self.enabled:
                self._append_unlocked("events", f"verbosity → {self.verbosity}")
                self._flush_unlocked()
            self._notify()
            return self.verbosity

    def snapshot(self, *, show_timestamps: bool = True) -> list[str]:
        with self._lock:
            return [line.display_text(show_timestamps=show_timestamps) for line in self.lines]

    def dump_text(self) -> str:
        with self._lock:
            if not self.lines:
                return ""
            return "\n".join(line.dump_text() for line in self.lines) + "\n"

    def _ensure_folder_unlocked(self) -> None:
        if self.folder is not None:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        folder = Path(self.project_root) / "runs" / f"lco-console-{stamp}"
        folder.mkdir(parents=True, exist_ok=True)
        self.folder = folder

    def _append(self, level: str, message: str) -> None:
        with self._lock:
            self._append_unlocked(level, message)
            self._notify()

    def _append_unlocked(self, level: str, message: str, *, force: bool = False) -> None:
        if not self.enabled and not force:
            return
        if not force:
            need = _LEVEL_RANK.get(level, 99)
            have = _LEVEL_RANK.get(self.verbosity, 1)
            if need > have:
                return
        stamp = time.strftime("%H:%M:%S")
        self.lines.append(ConsoleLine(stamp=stamp, level=level, message=str(message)))
        self._dirty = True

    def _flush_unlocked(self) -> Path | None:
        if self.folder is None:
            return None
        path = self.folder / "console.log"
        text = "\n".join(line.dump_text() for line in self.lines)
        path.write_text(text + ("\n" if self.lines else ""), encoding="utf-8")
        self._dirty = False
        return path

    def _notify(self) -> None:
        if self.on_change is None:
            return
        try:
            self.on_change()
        except Exception:  # noqa: BLE001
            pass
