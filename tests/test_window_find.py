"""Title-based window pick for deck-first re-anchor."""

from __future__ import annotations

import unittest

from idle_lab.window_find import WindowCandidate, pick_window_by_title


class PickWindowByTitleTests(unittest.TestCase):
    def test_exact_visible_match(self) -> None:
        cands = [
            WindowCandidate(1, "Other", 10, True, False),
            WindowCandidate(2, "BlueStacks App Player", 20, True, False),
        ]
        self.assertEqual(pick_window_by_title(cands, "BlueStacks App Player", our_pid=99), 2)

    def test_skips_our_pid(self) -> None:
        cands = [WindowCandidate(2, "Game", 99, True, False)]
        self.assertIsNone(pick_window_by_title(cands, "Game", our_pid=99))

    def test_prefers_visible_over_minimized(self) -> None:
        cands = [
            WindowCandidate(1, "Game", 10, True, True),
            WindowCandidate(2, "Game", 11, True, False),
        ]
        self.assertEqual(pick_window_by_title(cands, "Game", our_pid=1), 2)

    def test_ambiguous_same_quality_returns_none(self) -> None:
        cands = [
            WindowCandidate(1, "Game", 10, True, False),
            WindowCandidate(2, "Game", 11, True, False),
        ]
        self.assertIsNone(pick_window_by_title(cands, "Game", our_pid=1))

    def test_missing_title(self) -> None:
        cands = [WindowCandidate(1, "Game", 10, True, False)]
        self.assertIsNone(pick_window_by_title(cands, "Nope", our_pid=1))
        self.assertIsNone(pick_window_by_title(cands, "", our_pid=1))


if __name__ == "__main__":
    unittest.main()
