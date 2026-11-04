import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.automations.schema import (
    AutomationSchemaError,
    collection_from_dict,
    event_from_dict,
    resolve_branch,
    roi_from_dict,
)
from idle_lab.automations.store import AutomationStore
from idle_lab.presets import project_root


class RoiSchemaTests(unittest.TestCase):
    def test_valid_roi(self) -> None:
        roi = roi_from_dict({"id": "wave", "nx": 0.1, "ny": 0.2, "nw": 0.3, "nh": 0.1})
        self.assertEqual(roi.id, "wave")

    def test_rejects_out_of_bounds(self) -> None:
        with self.assertRaises(AutomationSchemaError):
            roi_from_dict({"id": "bad", "nx": 0.9, "ny": 0.9, "nw": 0.2, "nh": 0.2})


class EventSchemaTests(unittest.TestCase):
    def test_valid_event(self) -> None:
        event = event_from_dict(
            {
                "id": "tick",
                "title": "Tick",
                "priority": 10,
                "timing": {"type": "interval", "every_ms": 10000},
                "actions": [{"type": "log", "message": "hi"}],
            }
        )
        self.assertEqual(event.every_ms, 10000)

    def test_rejects_empty_actions(self) -> None:
        with self.assertRaises(AutomationSchemaError):
            event_from_dict(
                {
                    "id": "tick",
                    "title": "Tick",
                    "priority": 1,
                    "timing": {"type": "interval", "every_ms": 1000},
                    "actions": [],
                }
            )


class CollectionBranchTests(unittest.TestCase):
    def test_resolve_branch(self) -> None:
        collection = collection_from_dict(
            {
                "id": "main",
                "title": "Main",
                "children": ["ocr"],
                "branch_variable": "phase",
                "branches": {"begin": "phase_begin_stub", "mid": "phase_mid_stub"},
            }
        )
        self.assertEqual(resolve_branch(collection, {"phase": "MID"}), "phase_mid_stub")
        self.assertIsNone(resolve_branch(collection, {"phase": "unknown"}))


class StoreTests(unittest.TestCase):
    def test_shipped_samples_load(self) -> None:
        store = AutomationStore(project_root() / "automations")
        errors = store.load_all()
        self.assertEqual(errors, [])
        self.assertIn("ocr_ab_tick", store.events)
        self.assertIn("minute_clip", store.events)
        self.assertIn("humanize_upgrade_loop", store.events)
        self.assertIn("demo_poc", store.collections)
        self.assertIn("endgame_tier1", store.collections)
        self.assertIn("stat_collecting", store.collections)
        self.assertIn("endgame_phase_loop", store.collections)
        self.assertEqual(store.collections["stat_collecting"].title, "Stat collecting")
        self.assertEqual(store.collections["endgame_phase_loop"].title, "Endgame Phase Loop")
        self.assertEqual(
            store.collections["endgame_phase_loop"].children,
            ["endgame_status_buy", "stat_collect_30s", "stat_broll_5m"],
        )
        self.assertIn("endgame_status_buy", store.events)
        self.assertIn("endgame_minute_stats", store.events)
        self.assertIn("stat_collect_30s", store.events)
        self.assertIn("stat_broll_5m", store.events)
        self.assertTrue(store.events["endgame_status_buy"].enabled)
        self.assertFalse(store.events["humanize_upgrade_loop"].enabled)
        self.assertTrue(store.events["stat_collect_30s"].enabled)
        self.assertTrue(store.events["stat_broll_5m"].enabled)
        self.assertEqual(store.events["stat_collect_30s"].every_ms, 30000)
        self.assertEqual(store.events["stat_broll_5m"].every_ms, 300000)
        self.assertEqual(store.collections["stat_collecting"].children, ["stat_collect_30s", "stat_broll_5m"])
        types = {action.type for action in store.events["endgame_status_buy"].actions}
        self.assertIn("detect_panel", types)
        self.assertEqual(store.runtime.run_number, 1)

    def test_bad_file_reported(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "events").mkdir()
            (root / "events" / "bad.json").write_text(json.dumps({"id": "x"}), encoding="utf-8")
            store = AutomationStore(root)
            errors = store.load_all()
            self.assertEqual(len(errors), 1)
            self.assertEqual(store.events, {})


if __name__ == "__main__":
    unittest.main()
