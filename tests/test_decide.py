import unittest

from idle_lab.automations.decide import decide_ab, decide_branch


class DecideTests(unittest.TestCase):
    def test_contains_a(self) -> None:
        self.assertEqual(decide_ab("SIGNAL A", match_a="A", mode="contains"), "A")

    def test_falls_to_b(self) -> None:
        self.assertEqual(decide_ab("SIGNAL B", match_a="A", mode="contains"), "B")

    def test_equals(self) -> None:
        self.assertEqual(decide_ab("A", match_a="A", mode="equals"), "A")
        self.assertEqual(decide_ab("AA", match_a="A", mode="equals"), "B")

    def test_multi_branch(self) -> None:
        self.assertEqual(
            decide_branch("mid", {"begin": "b", "mid": "m", "end": "e"}, default="b"),
            "m",
        )


if __name__ == "__main__":
    unittest.main()
