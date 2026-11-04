import unittest

from idle_lab.automations.describe import format_collection, format_event
from idle_lab.automations.store import AutomationStore
from idle_lab.presets import project_root


class DescribeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = AutomationStore(project_root() / "automations")
        errors = self.store.load_all()
        self.assertEqual(errors, [])

    def test_event_basic_mentions_paths(self) -> None:
        event = self.store.events["ocr_ab_tick"]
        text = format_event(event, detailed=False, store=self.store)
        self.assertIn("UPPER", text)
        self.assertIn("LOWER", text)
        self.assertIn("Branches in contention", text)
        self.assertIn("Decided by", text)
        self.assertNotIn("runs/screenshots/", text)

    def test_event_detailed_includes_outputs(self) -> None:
        event = self.store.events["minute_clip"]
        text = format_event(event, detailed=True, store=self.store)
        self.assertIn("runs/clips/", text)
        self.assertIn("run_log.csv", text)
        self.assertIn("Exact steps", text)

    def test_collection_shows_branch_contention(self) -> None:
        collection = self.store.collections["demo_poc"]
        text = format_collection(collection, detailed=False, store=self.store)
        self.assertIn("Branches in contention", text)
        self.assertIn("phase", text)
        self.assertIn("Phase: Beginning", text)
        self.assertIn("Phase: Midgame", text)
        self.assertIn("Phase: Endgame", text)


if __name__ == "__main__":
    unittest.main()
