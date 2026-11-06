"""Append-only JSONL run traces under runs/traces/."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class TraceLog:
    """Thread-safe JSONL writer. Levels: off | failure | all."""

    def __init__(self, runs_dir: Path, *, level: str = "failure") -> None:
        self.runs_dir = Path(runs_dir)
        self.level = (level or "failure").strip().lower()
        if self.level not in {"off", "failure", "all"}:
            self.level = "failure"
        self._lock = threading.Lock()
        self._path: Path | None = None
        self._run_key: str | None = None

    def configure(self, *, level: str | None = None, run_number: int | None = None) -> None:
        if level is not None:
            key = level.strip().lower()
            self.level = key if key in {"off", "failure", "all"} else "failure"
        if run_number is not None:
            self._run_key = f"run_{int(run_number)}"
            self._path = None

    @property
    def enabled(self) -> bool:
        return self.level != "off"

    def _ensure_path(self) -> Path | None:
        if not self.enabled:
            return None
        if self._path is not None:
            return self._path
        traces = self.runs_dir / "traces"
        traces.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = f"{self._run_key or 'session'}_{stamp}.jsonl"
        self._path = traces / name
        return self._path

    def append(self, record: dict[str, Any], *, is_failure: bool = False) -> Path | None:
        if self.level == "off":
            return None
        if self.level == "failure" and not is_failure:
            return None
        path = self._ensure_path()
        if path is None:
            return None
        payload = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            **record,
        }
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return path
