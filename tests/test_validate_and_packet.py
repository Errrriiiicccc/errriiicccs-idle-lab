import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.automations.schema import Action, Event, Roi, event_from_dict
from idle_lab.automations.store import AutomationStore
from idle_lab.automations.validate import dry_run_event, validate_store
from idle_lab.prompt_packet import export_prompt_packet
from idle_lab.evidence import write_failure_pack
from idle_lab.trace_log import TraceLog
from idle_lab.ai_batch.iterations import begin_iteration, finalize_iteration, next_iteration_index


class ValidateTests(unittest.TestCase):
    def test_unknown_preset_flagged(self) -> None:
        store = AutomationStore.__new__(AutomationStore)
        store.rois = {"signal_roi": Roi(id="signal_roi", nx=0, ny=0, nw=0.1, nh=0.1)}
        store.events = {
            "e1": Event(
                id="e1",
                title="e1",
                priority=1,
                every_ms=1000,
                actions=[Action(type="play_preset", raw={"type": "play_preset", "preset": "missing"})],
                path="e1.json",
            )
        }
        store.collections = {}
        report = validate_store(store, preset_names={"ab choice a"})
        self.assertFalse(report.ok)

    def test_dry_run_lists_actions(self) -> None:
        event = event_from_dict(
            {
                "id": "demo",
                "title": "Demo",
                "priority": 1,
                "timing": {"type": "interval", "every_ms": 1000},
                "actions": [
                    {"type": "log", "message": "hi", "description": "Say hi"},
                    {"type": "wait_until", "variable": "signal", "equals": "A", "timeout_ms": 100},
                ],
            }
        )
        store = AutomationStore.__new__(AutomationStore)
        store.rois = {}
        lines = dry_run_event(event, store)
        self.assertTrue(any("wait_until" in line for line in lines))


class EvidenceTracePacketTests(unittest.TestCase):
    def test_failure_pack_and_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = write_failure_pack(root, error="boom", meta={"event_id": "x"})
            self.assertTrue((pack / "meta.json").is_file())
            trace = TraceLog(root, level="all")
            path = trace.append({"action_type": "log", "ok": True})
            self.assertIsNotNone(path)
            self.assertTrue(path.is_file())

    def test_prompt_packet_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "packet"
            export_prompt_packet(dest, goal="Press the shiny button.")
            self.assertTrue((dest / "PACKET.md").is_file())
            self.assertTrue((dest / "contract" / "ACTION_CATALOG.md").is_file())
            self.assertTrue((dest / "intent" / "GOAL.md").is_file())

    def test_iteration_folders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "mission"
            batch.mkdir()
            (batch / "batch.json").write_text("{}", encoding="utf-8")
            self.assertEqual(next_iteration_index(batch), 1)
            first = begin_iteration(batch)
            self.assertEqual(first.name, "001")
            finalize_iteration(first, run_report={"ok": True}, screen_map_slug="ai-run-x")
            self.assertTrue((first / "run_report.json").is_file())
            self.assertEqual(next_iteration_index(batch), 2)


class SchemaNewActionsTests(unittest.TestCase):
    def test_wait_until_and_match_template_parse(self) -> None:
        event = event_from_dict(
            {
                "id": "t",
                "title": "t",
                "priority": 1,
                "overdue_policy": "skip",
                "timing": {"type": "interval", "every_ms": 5000},
                "actions": [
                    {"type": "wait_until", "check": "variable", "variable": "signal", "equals": "A"},
                    {"type": "match_template", "template": "gem", "threshold": 0.9},
                ],
            }
        )
        self.assertEqual(event.overdue_policy, "skip")
        self.assertEqual(event.actions[0].type, "wait_until")
        self.assertEqual(event.actions[1].type, "match_template")


if __name__ == "__main__":
    unittest.main()
