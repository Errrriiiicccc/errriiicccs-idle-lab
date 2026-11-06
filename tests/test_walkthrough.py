import unittest

from idle_lab.automations.store import AutomationStore
from idle_lab.automations.walkthrough import Walkthrough
from idle_lab.presets import project_root


class WalkthroughTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = AutomationStore(project_root() / "automations")
        self.assertEqual(self.store.load_all(), [])

    def test_endgame_phase_loop_walkthrough(self) -> None:
        root = self.store.collections["endgame_phase_loop"]
        tour = Walkthrough(self.store, root)
        step = tour.start()
        self.assertEqual(step.kind, "intro")
        self.assertEqual(step.title, "Endgame Phase Loop")
        step = tour.advance_space()
        self.assertEqual(step.kind, "event_branch")
        self.assertEqual(step.title, "Endgame status + buy")
        step = tour.choose("B")
        self.assertEqual(step.kind, "path_preview")
        step = tour.advance_space()
        self.assertEqual(step.kind, "event")
        self.assertEqual(step.title, "Stat collect 30s")
        step = tour.advance_space()
        self.assertEqual(step.kind, "event")
        self.assertEqual(step.title, "B-roll every 5 minutes")
        step = tour.advance_space()
        self.assertEqual(step.kind, "done")

    def test_stat_collecting_walkthrough(self) -> None:
        root = self.store.collections["stat_collecting"]
        tour = Walkthrough(self.store, root)
        step = tour.start()
        self.assertEqual(step.kind, "intro")
        self.assertEqual(step.title, "Stat collecting")
        step = tour.advance_space()
        self.assertEqual(step.kind, "event")
        self.assertEqual(step.title, "Stat collect 30s")
        self.assertIn("30", step.body)
        step = tour.advance_space()
        self.assertEqual(step.kind, "event")
        self.assertEqual(step.title, "B-roll every 5 minutes")
        self.assertIn("20", step.body)
        step = tour.advance_space()
        self.assertEqual(step.kind, "done")

    def test_endgame_tier1_walkthrough(self) -> None:
        root = self.store.collections["endgame_tier1"]
        tour = Walkthrough(self.store, root)
        step = tour.start()
        self.assertEqual(step.kind, "intro")
        self.assertIn("Tier-1", step.body)
        step = tour.advance_space()
        self.assertEqual(step.kind, "event_branch")
        self.assertEqual(step.title, "Endgame status + buy")
        step = tour.choose("B")
        self.assertEqual(step.kind, "path_preview")
        body = step.body.lower()
        self.assertIn("defense", body)
        self.assertIn("health", body)
        self.assertIn("attack", body)
        self.assertIn("leave", body)
        self.assertIn("scroll", body)
        step = tour.advance_space()
        self.assertEqual(step.kind, "event_branch")
        self.assertEqual(step.title, "Endgame minute stats")
        step = tour.choose("A")
        self.assertEqual(step.kind, "path_preview")
        step = tour.advance_space()
        self.assertEqual(step.kind, "done")


if __name__ == "__main__":
    unittest.main()
