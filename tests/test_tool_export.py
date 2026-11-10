"""Tower tool_export reader + action schema."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.automations.schema import ACTION_TYPES, action_from_dict
from idle_lab.tool_export import ToolExportError, load_tool_export


class ToolExportTests(unittest.TestCase):
    def test_action_type_registered(self) -> None:
        self.assertIn("tool_export", ACTION_TYPES)
        action = action_from_dict({"type": "tool_export"})
        self.assertEqual(action.type, "tool_export")

    def test_load_maps_default_fields(self) -> None:
        payload = {
            "ExportVersion": 1,
            "DataVersion": 32,
            "ExportedAt": "2026-11-09T20:19:31.155Z",
            "CurrentWave": 582,
            "Coins": 937738.0352098646,
            "Gems": 134,
            "Cells": 4,
            "Stones": 1,
            "CurrentTier": 2,
            "CashEarnedThisRound": 17624246.54941769,
            "RoundActiveBool": True,
            "UserName": "Errriiiccc",
            "PlayTime": 300136.89,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toolExport_unknown.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            snap = load_tool_export(path)
        self.assertEqual(snap.variables["wave_number"], "582")
        self.assertEqual(snap.variables["gems"], "134")
        self.assertEqual(snap.variables["diamonds"], "134")
        self.assertEqual(snap.variables["tier"], "2")
        self.assertEqual(snap.variables["round_active"], "true")
        self.assertEqual(snap.variables["export_version"], "1")
        self.assertTrue(str(snap.variables["coins"]).startswith("937738"))
        self.assertEqual(snap.path, path)

    def test_stale_export_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toolExport_unknown.json"
            path.write_text(json.dumps({"CurrentWave": 1}), encoding="utf-8")
            # Force an old mtime.
            import os

            old = 1_700_000_000.0
            os.utime(path, (old, old))
            with self.assertRaises(ToolExportError):
                load_tool_export(path, max_age_s=1)

    def test_missing_file(self) -> None:
        with self.assertRaises(ToolExportError):
            load_tool_export(Path("C:/definitely/missing/tool_export.json"))


if __name__ == "__main__":
    unittest.main()
