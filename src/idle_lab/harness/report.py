"""Structured harness reports under runs/harness/<stamp>-<name>/."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from idle_lab.presets import project_root


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class HarnessReport:
    command: str
    name: str
    tier: str
    ok: bool
    started_at: str
    ended_at: str | None = None
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def finish(self, *, ok: bool, summary: str, details: dict[str, Any] | None = None) -> None:
        self.ok = ok
        self.summary = summary
        self.ended_at = now_iso()
        if details:
            self.details.update(details)


def report_dir(root: Path | None, name: str) -> Path:
    base = (root or project_root()) / "runs" / "harness"
    folder = base / f"{utc_stamp()}-{_safe_name(name)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_report(folder: Path, report: HarnessReport) -> Path:
    path = folder / "report.json"
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    report.artifacts.append(str(path))
    return path


def _safe_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name.strip())
    return cleaned.strip("-_") or "run"
