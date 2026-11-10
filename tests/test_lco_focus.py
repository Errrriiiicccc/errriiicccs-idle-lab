"""Molecule → LCO focus queue preview."""

from __future__ import annotations

import unittest
from pathlib import Path

from idle_lab.automations.lco_focus import (
    focus_token_for_event,
    preview_molecule_focus_actions,
)
from idle_lab.automations.schema import Action, Collection, Event
from idle_lab.automations.store import AutomationStore


def _event(eid: str, *actions: dict) -> Event:
    return Event(
        id=eid,
        title=eid,
        priority=50,
        every_ms=60000,
        actions=[Action(type=str(a["type"]), raw=dict(a)) for a in actions],
        enabled=False,
    )


class LcoFocusPreviewTests(unittest.TestCase):
    def test_flattens_nested_molecule_and_stat_collect(self) -> None:
        store = AutomationStore(Path("."))
        store.events = {
            "stat_collect": _event(
                "stat_collect",
                {"type": "tool_export"},
                {"type": "log", "message": "row"},
                {"type": "csv_append", "path": "stat_collect.csv", "fields": ["coins"]},
            ),
            "tab": _event("tab", {"type": "lco", "action": "tab_attack"}),
            "buy": _event(
                "buy",
                {"type": "lco", "action": "tab_attack"},
                {"type": "lco", "action": "buy_1"},
            ),
        }
        nested = Collection(
            id="nested",
            title="Nested",
            children=["tab", "buy"],
        )
        root = Collection(
            id="root",
            title="Root",
            children=["stat_collect", "nested"],
        )
        store.collections = {"nested": nested, "root": root}
        self.assertEqual(
            preview_molecule_focus_actions(root, store),
            ["stat_collect", "tab_attack", "tab_attack", "buy_1"],
        )
        self.assertEqual(focus_token_for_event(store.events["stat_collect"], store), "stat_collect")
        self.assertIsNone(focus_token_for_event(store.events["buy"], store))


class LcoRunActionFocusTests(unittest.TestCase):
    def test_run_action_sets_current_and_pack_queue(self) -> None:
        from unittest.mock import MagicMock

        from idle_lab.live_control.controller import LiveControlController
        from idle_lab.live_control.playbook import default_playbook_path, load_playbook
        from idle_lab.models import Rect
        from idle_lab.presets import project_root

        ctrl = LiveControlController(
            overlay=MagicMock(),
            project_root=project_root(),
            get_anchor=lambda: ("win", 1, Rect(0, 0, 100, 100)),
            async_actions=False,
        )
        ctrl.active = True
        ctrl.playbook = load_playbook(default_playbook_path(project_root()))
        painted: list[str] = []
        ctrl._repaint = lambda status: painted.append(status)  # type: ignore[method-assign]
        ctrl._dispatch = lambda action: None  # type: ignore[method-assign]

        ctrl.begin_external_pack("Test", ["tab_attack", "buy_1"])
        self.assertEqual(list(ctrl._pack_remaining), ["tab_attack", "buy_1"])
        self.assertEqual(ctrl._visible_queue(), ("tab_attack", "buy_1"))

        ctrl.run_action("tab_attack")
        self.assertEqual(list(ctrl._pack_remaining), ["buy_1"])
        self.assertIsNone(ctrl._current_action)
        self.assertIn("tab_attack", painted)
        self.assertTrue(any(s in {"…", "Ready"} or s == "tab_attack" for s in painted))


if __name__ == "__main__":
    unittest.main()
