"""lab-context.json loader."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.harness.classify import classify_hint
from idle_lab.harness.context import LabContextError, load_lab_context
from idle_lab.presets import project_root


class LabContextTests(unittest.TestCase):
    def test_project_context_loads_tower(self) -> None:
        ctx = load_lab_context(project_root())
        self.assertEqual(ctx.active_target, "tower")
        self.assertEqual(ctx.target.label, "The Tower")
        self.assertTrue(ctx.target.anchor_title_substrings)
        self.assertTrue(any("BlueStacks" in s for s in ctx.target.anchor_title_substrings))

    def test_missing_active_target_raises(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lab-context.json").write_text(
                json.dumps({"version": 1, "active_target": "missing", "targets": {"tower": {"label": "T"}}}),
                encoding="utf-8",
            )
            with self.assertRaises(LabContextError):
                load_lab_context(root)


class ClassifyTests(unittest.TestCase):
    def test_composer_is_story_tier(self) -> None:
        result = classify_hint("molecule composition save")
        self.assertEqual(result.tier, "T2")
        self.assertIn("composer-save-roundtrip", result.command)

    def test_ocr_is_fixture_tier(self) -> None:
        result = classify_hint("ocr perception")
        self.assertEqual(result.tier, "T1")

    def test_lco_is_live_tier(self) -> None:
        result = classify_hint("lco buy damage")
        self.assertEqual(result.tier, "T3")


if __name__ == "__main__":
    unittest.main()
