"""Feel Lab — Thread-first families + nested looks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from idle_lab.feel_lab import stages, store, themes


class FeelLabTests(unittest.TestCase):
    def test_home_tabs(self) -> None:
        self.assertEqual(stages.STAGES[0].id, "describe_feel")
        self.assertEqual(stages.STAGES[1].id, "change_theme")
        self.assertEqual(len(stages.STAGES[1].variants), len(themes.FAMILIES))

    def test_thread_is_main(self) -> None:
        self.assertEqual(themes.FAMILIES[0].id, "thread")
        self.assertEqual(themes.default_look().id, "thread_fine")
        self.assertTrue(themes.default_look().bold_live)
        # Light gray-green room (not near-black)
        self.assertGreater(int(themes.theme_by_id("thread_tall").bg[1:3], 16), 0x80)
        self.assertGreaterEqual(len(themes.FAMILIES[0].looks), 5)

    def test_resolve_and_pick(self) -> None:
        self.assertEqual(themes.resolve_look_id("rail_thread"), "thread_fine")
        self.assertEqual(themes.resolve_look_id(None), "thread_fine")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(store, "project_root", return_value=root):
                store.save_pick("change_theme", "thread_moss")
                data = store.load_picks()
                self.assertEqual(data["picks"]["change_theme"]["variant"], "thread_moss")


if __name__ == "__main__":
    unittest.main()
