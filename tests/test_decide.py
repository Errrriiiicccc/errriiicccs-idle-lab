import unittest

from idle_lab.automations.decide import decide_ab, decide_ab_with_reason, decide_branch


class DecideTests(unittest.TestCase):
    def test_contains_a(self) -> None:
        self.assertEqual(decide_ab("SIGNAL A", match_a="A", mode="contains"), "A")

    def test_falls_to_b(self) -> None:
        self.assertEqual(decide_ab("SIGNAL B", match_a="A", mode="contains"), "B")

    def test_equals(self) -> None:
        self.assertEqual(decide_ab("A", match_a="A", mode="equals"), "A")
        self.assertEqual(decide_ab("AA", match_a="A", mode="equals"), "B")

    def test_reason_explains_choice(self) -> None:
        branch, reason = decide_ab_with_reason("A", match_a="A", mode="equals")
        self.assertEqual(branch, "A")
        self.assertIn("PATH A", reason)
        branch_b, reason_b = decide_ab_with_reason("B", match_a="A", mode="equals")
        self.assertEqual(branch_b, "B")
        self.assertIn("PATH B", reason_b)
        self.assertIn("match failed", reason_b)

    def test_multi_branch(self) -> None:
        self.assertEqual(
            decide_branch("mid", {"begin": "b", "mid": "m", "end": "e"}, default="b"),
            "m",
        )


if __name__ == "__main__":
    unittest.main()
