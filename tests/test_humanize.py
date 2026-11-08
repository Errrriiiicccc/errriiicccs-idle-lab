import random
import unittest

from idle_lab.humanize import (
    HumanizeProfile,
    jitter_delay_ms,
    jitter_hold_ms,
    jitter_point,
    normalize_level,
    resolve_click,
)
from idle_lab.models import Rect


class HumanizeTests(unittest.TestCase):
    def test_normalize_falls_back_to_off(self) -> None:
        self.assertEqual(normalize_level("nope"), "off")
        self.assertEqual(normalize_level(None), "off")
        self.assertEqual(normalize_level("Heavy"), "heavy")

    def test_off_is_exact(self) -> None:
        profile = HumanizeProfile.from_level("off")
        rng = random.Random(1)
        self.assertEqual(jitter_delay_ms(500, profile, rng=rng), 500)
        self.assertEqual(jitter_hold_ms(50, profile, rng=rng), 50)
        self.assertEqual(jitter_point(100, 200, profile, rng=rng), (100, 200))
        resolved = resolve_click(100, 200, 50, profile, rng=rng)
        self.assertEqual((resolved.x, resolved.y, resolved.hold_ms), (100, 200, 50))
        self.assertEqual(resolved.move_steps, 0)

    def test_medium_varies_with_seed(self) -> None:
        profile = HumanizeProfile.from_level("medium")
        delays = {jitter_delay_ms(500, profile, rng=random.Random(seed)) for seed in range(20)}
        holds = {jitter_hold_ms(80, profile, rng=random.Random(seed)) for seed in range(20)}
        points = {jitter_point(400, 300, profile, rng=random.Random(seed)) for seed in range(30)}
        self.assertGreater(len(delays), 1)
        self.assertGreater(len(holds), 1)
        self.assertGreater(len(points), 1)
        for delay in delays:
            self.assertGreaterEqual(delay, 0)
            self.assertLessEqual(delay, 700)
        for hold in holds:
            self.assertGreaterEqual(hold, 1)

    def test_jitter_clamps_to_rect(self) -> None:
        profile = HumanizeProfile.from_level("heavy")
        rect = Rect(10, 10, 20, 20)
        rng = random.Random(0)
        for _ in range(40):
            x, y = jitter_point(15, 15, profile, rect=rect, rng=rng)
            self.assertGreaterEqual(x, rect.left)
            self.assertLess(x, rect.right)
            self.assertGreaterEqual(y, rect.top)
            self.assertLess(y, rect.bottom)

    def test_default_profile_is_off(self) -> None:
        self.assertEqual(HumanizeProfile().level, "off")
        self.assertFalse(HumanizeProfile().enabled)


if __name__ == "__main__":
    unittest.main()
