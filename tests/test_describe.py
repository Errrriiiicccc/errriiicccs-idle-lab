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
        event = self.store.events["buy_damage"]
        text = format_event(event, detailed=False, store=self.store)
        self.assertIn("Damage", text)
        self.assertIn("Branches in contention", text)
        self.assertIn("Decided by", text)

    def test_event_detailed_includes_outputs(self) -> None:
        event = self.store.events["stat_collect"]
        text = format_event(event, detailed=True, store=self.store)
        self.assertIn("Exact steps", text)
        self.assertTrue("stat_collect" in text.lower() or "tool_export" in text.lower() or "CSV" in text or "csv" in text)

    def test_collection_lists_children(self) -> None:
        collection = self.store.collections["endgame_phase_loop"]
        text = format_collection(collection, detailed=False, store=self.store)
        self.assertIn("Endgame Phase Loop", text)
        self.assertIn("Endgame status + buy", text)
        self.assertIn("Persistent state", text)


if __name__ == "__main__":
    unittest.main()
