"""T2 composer story + schema story."""

from __future__ import annotations

import unittest

from idle_lab.harness.stories import list_stories, run_story
from idle_lab.presets import project_root


class HarnessStoryTests(unittest.TestCase):
    def test_stories_are_seeded(self) -> None:
        ids = {item["id"] for item in list_stories(project_root())}
        self.assertIn("composer-save-roundtrip", ids)
        self.assertIn("molecule-dry-run", ids)
        self.assertIn("schema-validate-all", ids)

    def test_composer_save_roundtrip(self) -> None:
        result = run_story("composer-save-roundtrip", root=project_root())
        self.assertTrue(result.ok, result.summary)
        self.assertTrue(result.details.get("library_has_molecule"))
        self.assertTrue(result.details.get("validation_ok"))

    def test_schema_validate_all(self) -> None:
        # Story must run and report structure even when the repo has known issues
        # (currently ocr_ab_tick references a missing preset).
        result = run_story("schema-validate-all", root=project_root())
        self.assertIn("issue_count", result.details)
        self.assertIsInstance(result.details["issues"], list)
        self.assertTrue(result.summary.startswith("validate:"))

    def test_molecule_dry_run(self) -> None:
        result = run_story("molecule-dry-run", root=project_root())
        self.assertTrue(result.ok, result.summary)
        self.assertTrue(any("buy_health" in line or "PLAN" in line for line in result.lines))


if __name__ == "__main__":
    unittest.main()
