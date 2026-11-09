"""T1 fixture benches — start with OCR crops."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.automations.ocr_bench import DEFAULT_FIXTURE_DIR, run_fixture_bench
from idle_lab.presets import project_root


class FixtureError(RuntimeError):
    """Unknown or failed fixture bench."""


@dataclass
class FixtureResult:
    ok: bool
    bench: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


def run_fixture_bench_named(bench: str, *, root: Path | None = None) -> FixtureResult:
    name = (bench or "").strip().casefold()
    project = root or project_root()
    if name in {"ocr", "ocr-fixture", "ocr_fixture", "ocr-fixture-bench"}:
        fixture_dir = project / "tests" / "fixtures" / "ocr"
        if not fixture_dir.exists():
            fixture_dir = DEFAULT_FIXTURE_DIR
        report = run_fixture_bench(fixture_dir=fixture_dir, manifest_name="manifest.json")
        summary = (
            f"OCR fixture bench: {report.passed}/{report.total} passed"
            + (f", {report.failed} failed" if report.failed else "")
            + (f", {report.missing} missing" if report.missing else "")
        )
        return FixtureResult(
            ok=report.ok,
            bench="ocr",
            summary=summary,
            details=report.to_dict(),
        )
    raise FixtureError(f"unknown fixture bench {bench!r}; known: ocr")
