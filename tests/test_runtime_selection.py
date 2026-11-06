import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.schema import Action, Event
from idle_lab.automations.store import AutomationStore


class RuntimeSelectionTests(unittest.TestCase):
    def test_start_selection_ignores_other_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AutomationStore.__new__(AutomationStore)
            store.runtime = MagicMock(run_number=1)
            store.rois = {}
            store.events = {
                "keep": Event(
                    id="keep",
                    title="keep",
                    priority=10,
                    every_ms=5000,
                    actions=[Action(type="log", raw={"type": "log", "message": "k"})],
                    enabled=True,
                ),
                "other": Event(
                    id="other",
                    title="other",
                    priority=10,
                    every_ms=5000,
                    actions=[Action(type="log", raw={"type": "log", "message": "o"})],
                    enabled=True,
                ),
            }
            runtime = AutomationRuntime(
                store=store,
                runs_dir=Path(tmp),
                get_anchor_rect=lambda: None,
            )
            runtime.start(event_ids=["keep"])
            try:
                ids = {event.id for event in runtime._loop_events()}
                self.assertEqual(ids, {"keep"})
            finally:
                runtime.stop()


if __name__ == "__main__":
    unittest.main()
