"""Regression bench: committed ROI crops → typed inferences.

Prefer running this via Missions → **OCR fixture bench** → Start (writes
``ai-batches/ocr-fixture-bench/run_report.json``). This unittest wraps the
same ``run_fixture_bench`` helper for CI / quick local checks.
"""

from __future__ import annotations

import unittest

from idle_lab.automations.ocr_bench import run_fixture_bench


class OcrFixtureBench(unittest.TestCase):
    def test_manifest_cases(self) -> None:
        report = run_fixture_bench()
        if not report.ok:
            self.fail(report.summary() + "\n" + "\n".join(
                f"  {case.file}: got {case.inference!r} want {case.accepted}"
                + (f" err={case.error}" if case.error else "")
                for case in report.cases
                if not case.ok
            ))


if __name__ == "__main__":
    unittest.main()
