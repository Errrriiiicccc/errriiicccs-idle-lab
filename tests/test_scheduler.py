import unittest

from idle_lab.automations.scheduler import Scheduler, recording_blocks_ab
from idle_lab.automations.schema import Event, Action


def make_event(event_id: str, priority: int, every_ms: int = 1000) -> Event:
    return Event(
        id=event_id,
        title=event_id,
        priority=priority,
        every_ms=every_ms,
        actions=[Action(type="log", raw={"type": "log", "message": "x"})],
        enabled=True,
    )


class SchedulerTests(unittest.TestCase):
    def test_recording_blocks_ab_helper(self) -> None:
        self.assertTrue(recording_blocks_ab(100, 10))
        self.assertFalse(recording_blocks_ab(10, 100))

    def test_higher_priority_runs_and_defers_lower(self) -> None:
        clock = {"now": 0.0}
        scheduler = Scheduler(clock=lambda: clock["now"])
        ab = make_event("ocr_ab_tick", 10, every_ms=10000)
        clip = make_event("minute_clip", 100, every_ms=60000)
        scheduler.reset([ab, clip], stagger=False)

        clock["now"] = 0.0
        chosen = scheduler.pick_due([ab, clip])
        self.assertEqual(chosen.id, "minute_clip")
        scheduler.mark_running(clip)

        clock["now"] = 5.0
        blocked = scheduler.pick_due([ab, clip])
        self.assertIsNone(blocked)
        snapshot = {item.event_id: item.status for item in scheduler.queue_snapshot()}
        self.assertEqual(snapshot["minute_clip"], "running")
        self.assertEqual(snapshot["ocr_ab_tick"], "deferred")

        scheduler.mark_finished(clip, [ab, clip])
        clock["now"] = 5.1
        # clip next fire is far away; ab should be eligible if due
        scheduler._next_fire["ocr_ab_tick"] = 0.0
        chosen = scheduler.pick_due([ab, clip])
        self.assertEqual(chosen.id, "ocr_ab_tick")


if __name__ == "__main__":
    unittest.main()
