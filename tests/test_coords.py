import unittest

from idle_lab.models import Rect, normalized_to_screen, screen_to_normalized, timing_for_point
from idle_lab.recorder import Recorder


class CoordTests(unittest.TestCase):
    def test_edges_use_the_last_pixel_inside_the_window(self) -> None:
        rect = Rect(0, 0, 101, 51)
        self.assertEqual(normalized_to_screen(rect, 0, 0), (0, 0))
        self.assertEqual(normalized_to_screen(rect, 1, 1), (100, 50))

    def test_negative_monitor_origin(self) -> None:
        rect = Rect(-1920, 10, -1, 210)
        self.assertEqual(normalized_to_screen(rect, 0, 0), (-1920, 10))
        self.assertEqual(normalized_to_screen(rect, 1, 1), (-2, 209))

    def test_round_trip(self) -> None:
        rect = Rect(100, 40, 1100, 840)
        for nx, ny in ((0, 0), (0.25, 0.25), (0.5, 0.5), (1, 1)):
            x, y = normalized_to_screen(rect, nx, ny)
            back_x, back_y = screen_to_normalized(rect, x, y)
            self.assertEqual(normalized_to_screen(rect, back_x, back_y), (x, y))

    def test_timing_modes(self) -> None:
        self.assertEqual(timing_for_point("instantaneous", gap_ms=400, held_ms=200), (50, 50))
        self.assertEqual(timing_for_point("one_second", gap_ms=10, held_ms=10), (950, 50))
        self.assertEqual(timing_for_point("realtime", gap_ms=400, held_ms=80), (400, 80))
        self.assertEqual(timing_for_point("realtime", gap_ms=-5, held_ms=10), (0, 50))


class RecorderTests(unittest.TestCase):
    def test_realtime_gap_and_hold(self) -> None:
        clock = {"now": 0.0}
        recorder = Recorder(clock=lambda: clock["now"])
        recorder.start("route", "realtime")
        rect = Rect(0, 0, 101, 101)
        clock["now"] = 0.2
        recorder.space_down(10, 10)
        clock["now"] = 0.28
        first = recorder.space_up(lambda: rect)
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first.delay_ms, 200)
        self.assertEqual(first.hold_ms, 80)
        clock["now"] = 0.68
        recorder.space_down(100, 50)
        clock["now"] = 0.69
        second = recorder.space_up(lambda: rect)
        self.assertIsNotNone(second)
        assert second is not None
        self.assertEqual(second.delay_ms, 400)
        self.assertEqual(second.hold_ms, 50)
        self.assertAlmostEqual(second.nx, 1.0)
        self.assertAlmostEqual(second.ny, 0.5)

    def test_fixed_modes_ignore_the_clock(self) -> None:
        clock = {"now": 0.0}
        recorder = Recorder(clock=lambda: clock["now"])
        recorder.start("fast", "instantaneous")
        rect = Rect(0, 0, 201, 201)
        clock["now"] = 2
        recorder.space_down(0, 0)
        clock["now"] = 3
        point = recorder.space_up(lambda: rect)
        self.assertIsNotNone(point)
        assert point is not None
        self.assertEqual((point.delay_ms, point.hold_ms), (50, 50))

    def test_missing_anchor_skips_the_point(self) -> None:
        recorder = Recorder(clock=lambda: 1.0)
        recorder.start("x", "one_second")
        recorder.space_down(5, 5)
        self.assertIsNone(recorder.space_up(lambda: None))
        self.assertEqual(recorder.points, [])
        self.assertIn("not available", recorder.last_error)


if __name__ == "__main__":
    unittest.main()
