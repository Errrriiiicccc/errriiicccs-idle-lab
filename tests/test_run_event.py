"""run_event composition + store validation for split buy atoms."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.schema import ACTION_TYPES, Action, Event
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.validate import dry_run_event, validate_store
from idle_lab.models import Rect


class RunEventTests(unittest.TestCase):
    def test_action_type_registered(self) -> None:
        self.assertIn("run_event", ACTION_TYPES)

    def test_store_loads_composed_buys(self) -> None:
        root = Path(__file__).resolve().parents[1] / "automations"
        store = AutomationStore(root)
        store.load_all()
        for event_id in ("gem_box_check", "buy_health", "buy_damage", "endgame_status_buy"):
            self.assertIn(event_id, store.events)
        self.assertIn("health_then_damage", store.collections)
        report = validate_store(
            store,
            preset_names={
                "gem box tap",
                "currency toggle",
                "humanize atk def loop",
                "ab choice a",
                "ab choice b",
            },
        )
        errors = [
            f"{issue.path}: {issue.message}"
            for issue in report.issues
            if issue.level == "error"
            and any(name in (issue.path or "") for name in ("endgame_status_buy", "buy_health", "buy_damage", "gem_box_check", "health_then_damage"))
        ]
        self.assertEqual(errors, [], msg=errors)
        plan = "\n".join(dry_run_event(store.events["endgame_status_buy"], store))
        self.assertIn("run_event", plan)
        self.assertIn("buy_health", plan)
        self.assertIn("buy_damage", plan)

    def test_run_event_executes_child_actions(self) -> None:
        child = Event(
            id="child_atom",
            title="Child",
            priority=1,
            every_ms=1000,
            actions=[Action(type="log", raw={"type": "log", "message": "from-child", "level": "ok"})],
        )
        parent = Event(
            id="parent_atom",
            title="Parent",
            priority=1,
            every_ms=1000,
            actions=[Action(type="run_event", raw={"type": "run_event", "event": "child_atom"})],
        )
        store = MagicMock()
        store.events = {"child_atom": child, "parent_atom": parent}
        store.runtime.run_number = 1
        with tempfile.TemporaryDirectory() as folder:
            runtime = AutomationRuntime(
                store=store,
                runs_dir=Path(folder),
                get_anchor_rect=lambda: Rect(0, 0, 100, 100),
            )
            logs: list[str] = []
            runtime.log = lambda message, level="info": logs.append(message)  # type: ignore[method-assign]
            runtime._run_event(parent)
            self.assertTrue(any("from-child" in line for line in logs))
            self.assertTrue(any("child_atom" in line for line in logs))

    def test_run_event_cycle_raises(self) -> None:
        a = Event(
            id="a",
            title="A",
            priority=1,
            every_ms=1000,
            actions=[Action(type="run_event", raw={"type": "run_event", "event": "b"})],
        )
        b = Event(
            id="b",
            title="B",
            priority=1,
            every_ms=1000,
            actions=[Action(type="run_event", raw={"type": "run_event", "event": "a"})],
        )
        store = MagicMock()
        store.events = {"a": a, "b": b}
        store.runtime.run_number = 1
        with tempfile.TemporaryDirectory() as folder:
            runtime = AutomationRuntime(
                store=store,
                runs_dir=Path(folder),
                get_anchor_rect=lambda: Rect(0, 0, 100, 100),
            )
            runtime.log = lambda message, level="info": None  # type: ignore[method-assign]
            with self.assertRaises(RuntimeError) as ctx:
                runtime._run_event(a)
            self.assertIn("cycle", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
