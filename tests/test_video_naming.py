import unittest

from idle_lab.automations.video import clip_name


class VideoNamingTests(unittest.TestCase):
    def test_clip_name(self) -> None:
        self.assertEqual(clip_name(1, 42), "run_1_wave_42")
        self.assertEqual(clip_name(1, "xx"), "run_1_wave_xx")
        self.assertEqual(
            clip_name(1, 600, kind="broll", stamp="20261104-143000"),
            "broll_run_1_wave_600_20261104-143000",
        )


if __name__ == "__main__":
    unittest.main()
