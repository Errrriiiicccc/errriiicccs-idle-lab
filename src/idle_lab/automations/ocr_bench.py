"""OCR fixture bench — same cases Missions run via ``ocr_fixture_bench``.

Committed crops live under ``tests/fixtures/ocr/``. The unittest wrapper and the
AI-batch step both call ``run_fixture_bench`` so Eric never has to run pytest
by hand for perception regressions.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from idle_lab.automations.ocr import configure_tesseract, ocr_field

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "ocr"
DEFAULT_MANIFEST = DEFAULT_FIXTURE_DIR / "manifest.json"


@dataclass
class BenchCaseResult:
    file: str
    parse_as: str
    expect: str
    accepted: list[str]
    inference: str
    observation: str
    prep: str | None
    select: str | None
    ok: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchReport:
    ok: bool
    total: int
    passed: int
    failed: int
    missing: int
    cases: list[BenchCaseResult] = field(default_factory=list)
    manifest: str = ""
    fixture_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "missing": self.missing,
            "manifest": self.manifest,
            "fixture_dir": self.fixture_dir,
            "cases": [case.to_dict() for case in self.cases],
            "failures": [
                case.to_dict()
                for case in self.cases
                if not case.ok
            ],
        }

    def summary(self) -> str:
        if self.ok:
            return f"OCR fixture bench PASS ({self.passed}/{self.total})"
        bits = [
            f"{case.file}: got {case.inference!r} want {case.accepted}"
            for case in self.cases
            if not case.ok
        ]
        head = f"OCR fixture bench FAIL ({self.passed}/{self.total} passed)"
        if not bits:
            return head
        return head + " — " + "; ".join(bits[:6]) + ("…" if len(bits) > 6 else "")


def resolve_fixture_dir(path: str | Path | None = None) -> Path:
    if path is None or str(path).strip() in ("", "default"):
        return DEFAULT_FIXTURE_DIR
    candidate = Path(path)
    if candidate.is_dir():
        return candidate
    # Relative to repo root (parent of tests/ or src/)
    repo = Path(__file__).resolve().parents[3]
    alt = repo / candidate
    if alt.is_dir():
        return alt
    return candidate


def run_fixture_bench(
    *,
    fixture_dir: str | Path | None = None,
    manifest_name: str = "manifest.json",
) -> BenchReport:
    """Run every manifest case. Never raises for OCR mismatches — report.ok says pass/fail."""

    root = resolve_fixture_dir(fixture_dir)
    manifest_path = root / manifest_name
    report = BenchReport(
        ok=False,
        total=0,
        passed=0,
        failed=0,
        missing=0,
        manifest=str(manifest_path),
        fixture_dir=str(root),
    )
    if not manifest_path.is_file():
        report.cases.append(
            BenchCaseResult(
                file=manifest_name,
                parse_as="",
                expect="",
                accepted=[],
                inference="",
                observation="",
                prep=None,
                select=None,
                ok=False,
                error=f"manifest missing: {manifest_path}",
            )
        )
        report.total = 1
        report.failed = 1
        report.missing = 1
        return report

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = list(data.get("cases") or [])
    configure_tesseract()

    for case in cases:
        if not isinstance(case, dict):
            continue
        report.total += 1
        file_name = str(case.get("file") or "")
        parse_as = str(case.get("parse_as") or "raw")
        expect = str(case.get("expect") or "")
        accepted = [str(item) for item in (case.get("accept") or [])]
        if expect and expect not in accepted:
            accepted.append(expect)
        path = root / file_name
        if not path.is_file():
            report.missing += 1
            report.failed += 1
            report.cases.append(
                BenchCaseResult(
                    file=file_name,
                    parse_as=parse_as,
                    expect=expect,
                    accepted=accepted,
                    inference="",
                    observation="",
                    prep=None,
                    select=None,
                    ok=False,
                    error="fixture file missing",
                )
            )
            continue
        try:
            image = Image.open(path).convert("RGB")
            result = ocr_field(image, parse_as=parse_as)
            ok = result.inference in accepted
            if ok:
                report.passed += 1
            else:
                report.failed += 1
            report.cases.append(
                BenchCaseResult(
                    file=file_name,
                    parse_as=parse_as,
                    expect=expect,
                    accepted=accepted,
                    inference=result.inference,
                    observation=result.observation,
                    prep=result.meta.get("prep"),
                    select=result.meta.get("select"),
                    ok=ok,
                )
            )
        except Exception as exc:  # noqa: BLE001 — capture per-case
            report.failed += 1
            report.cases.append(
                BenchCaseResult(
                    file=file_name,
                    parse_as=parse_as,
                    expect=expect,
                    accepted=accepted,
                    inference="",
                    observation="",
                    prep=None,
                    select=None,
                    ok=False,
                    error=str(exc),
                )
            )

    report.ok = report.failed == 0 and report.total > 0
    return report
