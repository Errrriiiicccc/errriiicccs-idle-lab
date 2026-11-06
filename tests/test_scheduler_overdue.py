import unittest

from idle_lab.automations.scheduler import Scheduler
from idle_lab.automations.schema import Action, Event


def make_event(event_id: str, priority: int, every_ms: int = 1000, policy: str = "run_when_free") -> Event:
    return Event(
        id=event_id,
        title=event_id,
        priority=priority,
        every_ms=every_ms,
        actions=[Action(type="log", raw={"type": "log", "message": "x"})],
        enabled=True,
        overdue_policy=policy,
    )


class OverduePolicyTests(unittest.TestCase):
    def test_skip_policy_reschedules_loser(self) -> None:
        clock = {"now": 0.0}
        scheduler = Scheduler(clock=lambda: clock["now"])
        high = make_event("high", 100, every_ms=10000)
        low = make_event("low", 10, every_ms=1000, policy="skip")
        scheduler.reset([high, low], stagger=False)
        clock["now"] = 0.0
        chosen = scheduler.pick_due([high, low])
        self.assertEqual(chosen.id, "high")
        messages = scheduler.take_skip_messages()
        self.assertTrue(any("skipped low" in msg for msg in messages))
        # low next fire pushed into the future
        self.assertGreater(scheduler._next_fire["low"], clock["now"])

    def test_deferred_reason_names_blocker(self) -> None:
        clock = {"now": 0.0}
        scheduler = Scheduler(clock=lambda: clock["now"])
        high = make_event("high", 100)
        low = make_event("low", 10)
        scheduler.reset([high, low], stagger=False)
        scheduler.mark_running(high)
        clock["now"] = 1.0
        self.assertIsNone(scheduler.pick_due([high, low]))
        snap = {item.event_id: item.detail for item in scheduler.queue_snapshot()}
        self.assertIn("high", snap["low"])


if __name__ == "__main__":
    unittest.main()
