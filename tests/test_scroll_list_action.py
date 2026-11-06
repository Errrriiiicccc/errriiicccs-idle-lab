"""scroll_list action + atom once smoke (no live window)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.schema import ACTION_TYPES
from idle_lab.automations.store import AutomationStore
from idle_lab.models import Rect


class ScrollListActionTests(unittest.TestCase):
    def test_scroll_list_in_action_types(self) -> None:
        self.assertIn("scroll_list", ACTION_TYPES)

    def test_scroll_list_drags_rows_times(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "events").mkdir()
            (root / "events" / "scroll.json").write_text(
                '{"id":"scroll","title":"S","priority":1,"enabled":false,'
                '"timing":{"type":"interval","every_ms":60000},'
                '"actions":[{"type":"scroll_list","direction":"down","rows":2,'
                '"settle_ms":0}]}\n',
                encoding="utf-8",
            )
            store = AutomationStore(root)
            store.load_all()
            rect = Rect(0, 0, 100, 200)
            runtime = AutomationRuntime(
                store=store,
                runs_dir=root / "runs",
                get_anchor_rect=lambda: rect,
                get_anchor_hwnd=lambda: (1, rect),
            )
            with patch("idle_lab.automations.runtime.drag_list") as drag:
                runtime._run_event(store.events["scroll"])  # noqa: SLF001
            self.assertEqual(drag.call_count, 2)
            self.assertEqual(runtime.state.variables.get("scroll_list_rows"), "2")

    def test_run_event_once_completes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "events").mkdir()
            (root / "events" / "log.json").write_text(
                '{"id":"log","title":"L","priority":1,"enabled":false,'
                '"timing":{"type":"interval","every_ms":60000},'
                '"actions":[{"type":"log","message":"hi"}]}\n',
                encoding="utf-8",
            )
            store = AutomationStore(root)
            store.load_all()
            runtime = AutomationRuntime(
                store=store,
                runs_dir=root / "runs",
                get_anchor_rect=lambda: Rect(0, 0, 10, 10),
            )
            runtime.run_event_once("log")
            thread = runtime._collection_thread  # noqa: SLF001
            assert thread is not None
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(runtime.collection_running)
            # Second once is allowed after the first finishes.
            runtime.run_event_once("log")
            thread2 = runtime._collection_thread  # noqa: SLF001
            assert thread2 is not None
            thread2.join(timeout=5)
            self.assertFalse(thread2.is_alive())


if __name__ == "__main__":
    unittest.main()
