"""T0 — thin unittest wrapper for harness CLI."""

from __future__ import annotations

import unittest
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnitResult:
    ok: bool
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


_SURFACE_MODULES: dict[str, list[str]] = {
    "composer": ["tests.test_composer"],
    "schema": ["tests.test_automations_schema", "tests.test_taxonomy"],
    "ocr": ["tests.test_ocr_fixtures", "tests.test_ocr_parse", "tests.test_hud_mode"],
    "harness": [
        "tests.test_harness_context",
        "tests.test_harness_story_composer",
        "tests.test_harness_doctor",
    ],
    "ai_batch": ["tests.test_ai_batch_runner"],
}


def run_units(targets: list[str] | None = None) -> UnitResult:
    """Run unittest modules. Empty targets → a small default harness smoke set."""

    modules: list[str] = []
    raw = list(targets or [])
    if not raw:
        modules = [
            "tests.test_harness_context",
            "tests.test_harness_story_composer",
            "tests.test_composer",
        ]
    else:
        for item in raw:
            key = item.strip()
            if not key:
                continue
            if key in _SURFACE_MODULES:
                modules.extend(_SURFACE_MODULES[key])
            elif key.startswith("tests."):
                modules.append(key)
            elif key.startswith("test_"):
                modules.append(f"tests.{key}")
            else:
                modules.append(key)

    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for mod in modules:
        if mod not in seen:
            seen.add(mod)
            ordered.append(mod)

    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for mod in ordered:
        suite.addTests(loader.loadTestsFromName(mod))

    result = unittest.TestResult()
    suite.run(result)
    ok = result.wasSuccessful()
    failed = len(result.failures) + len(result.errors)
    summary = (
        f"unittest: {result.testsRun} run, {failed} failed"
        if not ok
        else f"unittest: {result.testsRun} run, all ok"
    )
    details: dict[str, Any] = {
        "modules": ordered,
        "tests_run": result.testsRun,
        "failures": [
            {"test": str(test), "message": traceback}
            for test, traceback in result.failures
        ],
        "errors": [
            {"test": str(test), "message": traceback}
            for test, traceback in result.errors
        ],
    }
    return UnitResult(ok=ok, summary=summary, details=details)
