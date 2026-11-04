import unittest

from idle_lab.automations.store import AutomationStore
from idle_lab.automations.walkthrough import Walkthrough
from idle_lab.presets import project_root


class WalkthroughTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = AutomationStore(project_root() / "automations")
        self.assertEqual(self.store.load_all(), [])
        self.root = self.store.collections["demo_poc"]

    def test_intro_then_events_then_branches(self) -> None:
        tour = Walkthrough(self.store, self.root)
        step = tour.start()
        self.assertEqual(step.kind, "intro")
        step = tour.advance_space()
        self.assertEqual(step.kind, "event_branch")
        self.assertEqual(step.title, "OCR A/B tick")
        self.assertIn("A", step.branch_targets)
        self.assertIn("B", step.branch_targets)
        step = tour.choose("A")
        self.assertEqual(step.kind, "path_preview")
        self.assertIn("PATH A", step.title)
        step = tour.advance_space()
        self.assertEqual(step.kind, "event")
        self.assertEqual(step.title, "Minute clip")
        step = tour.advance_space()
        self.assertEqual(step.kind, "collection_branch")
        self.assertGreaterEqual(len(step.choices), 3)
        self.assertEqual(step.choices[0].key, "A")
        self.assertEqual(step.choices[1].key, "B")
        self.assertEqual(step.choices[2].key, "C")
        step = tour.choose("B")
        self.assertEqual(step.kind, "intro")
        self.assertIn("Midgame", step.title)
        # finish stub collection quickly
        step = tour.advance_space()  # intro -> children empty -> branches? none -> leave -> back to branches
        # may land on collection_branch again
        self.assertIn(step.kind, {"collection_branch", "done", "intro", "event"})

    def test_space_skips_collection_branches_to_done(self) -> None:
        tour = Walkthrough(self.store, self.root)
        tour.start()
        tour.advance_space()  # ocr ab
        tour.choose("B")
        tour.advance_space()  # after path
        tour.advance_space()  # after minute clip -> branches
        step = tour.advance_space()  # skip branches
        self.assertEqual(step.kind, "done")
        self.assertIsNone(tour.advance_space())


if __name__ == "__main__":
    unittest.main()
