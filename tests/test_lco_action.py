"""lco action: atoms drive a headless Live Control session (no live window)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PIL import Image

from idle_lab.automations.runtime import AutomationRuntime
from idle_lab.automations.schema import ACTION_TYPES, Action, Event
from idle_lab.automations.validate import validate_store
from idle_lab.live_control.buy_detect import BuyGridDetection, DetectedBuySlot
from idle_lab.live_control.controller import LiveControlError
from idle_lab.models import Rect

REPO_MAP = Path(__file__).resolve().parents[1] / "automations" / "maps" / "tower_main_gameplay.objects.json"
CONTROLLER = "idle_lab.live_control.controller"


def _event(*actions: dict) -> Event:
    return Event(
        id="lco_atom",
        title="LCO atom",
        priority=1,
        every_ms=60000,
        actions=[Action(type=str(raw["type"]), raw=raw) for raw in actions],
    )


def _grid() -> BuyGridDetection:
    slots = [DetectedBuySlot(index=i + 1, nx=0.3 + 0.3 * (i % 2), ny=0.7 + 0.1 * (i // 2)) for i in range(6)]
    return BuyGridDetection(snapped=True, slots=slots, reason="fake grid", row_nys=(0.7, 0.8, 0.9), header_ny=None)


class LcoActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "automations" / "maps").mkdir(parents=True)
        shutil.copy(REPO_MAP, root / "automations" / "maps" / REPO_MAP.name)
        rect = Rect(0, 0, 593, 1028)
        store = MagicMock()
        store.events = {}
        store.runtime.run_number = 1
        self.runtime = AutomationRuntime(
            store=store,
            runs_dir=root / "runs",
            get_anchor_rect=lambda: rect,
            get_anchor_hwnd=lambda: (1, rect),
        )
        self.runtime.log = lambda message, level="info": None  # type: ignore[method-assign]
        panel = SimpleNamespace(panel_open=True, tab="defense", mean_rgb=(0.0, 0.0, 0.0), reason="fake panel")
        self.patches = [
            patch(f"{CONTROLLER}.grab_anchor", return_value=Image.new("RGB", (593, 1028))),
            patch(f"{CONTROLLER}.detect_upgrade_panel", return_value=panel),
            patch(f"{CONTROLLER}.detect_buy_grid", return_value=_grid()),
            patch(f"{CONTROLLER}.seek_list_top"),
        ]
        self.grab = self.patches[0].start()
        for extra in self.patches[1:]:
            extra.start()
        self.click = patch(f"{CONTROLLER}.click_normalized").start()
        self.patches.append(self.click)

    def tearDown(self) -> None:
        patch.stopall()
        self._tmp.cleanup()

    def test_action_type_registered(self) -> None:
        self.assertIn("lco", ACTION_TYPES)

    def test_key_resolves_and_repeats_on_detected_slot(self) -> None:
        self.runtime._run_event(_event({"type": "lco", "key": "3", "times": 2}))  # noqa: SLF001
        self.assertEqual(self.click.call_count, 2)
        kwargs = self.click.call_args.kwargs
        self.assertAlmostEqual(kwargs["nx"], 0.3)
        self.assertAlmostEqual(kwargs["ny"], 0.8)
        self.assertEqual(self.runtime.state.variables["lco_tab"], "defense")
        self.assertEqual(self.runtime.state.variables["lco_aligned"], "yes")

    def test_session_spans_atom_then_exits(self) -> None:
        self.runtime._run_event(  # noqa: SLF001
            _event({"type": "lco", "action": "buy_1"}, {"type": "lco", "action": "buy_2"})
        )
        self.assertEqual(self.grab.call_count, 1)
        assert self.runtime._lco is not None  # noqa: SLF001
        self.assertFalse(self.runtime._lco.active)  # noqa: SLF001

    def test_tab_action_clicks_and_homes(self) -> None:
        self.runtime._run_event(_event({"type": "lco", "action": "tab_attack"}))  # noqa: SLF001
        self.assertEqual(self.click.call_count, 1)
        self.assertEqual(self.runtime.state.variables["lco_tab"], "attack")

    def test_unbound_key_raises_and_session_ends(self) -> None:
        with self.assertRaises(LiveControlError):
            self.runtime._run_event(_event({"type": "lco", "key": "Z"}))  # noqa: SLF001
        assert self.runtime._lco is not None  # noqa: SLF001
        self.assertFalse(self.runtime._lco.active)  # noqa: SLF001

    def test_describe_is_not_actuatable(self) -> None:
        with self.assertRaises(LiveControlError):
            self.runtime._run_event(_event({"type": "lco", "key": "D"}))  # noqa: SLF001

    def test_stop_interrupts_session(self) -> None:
        self.runtime._lco_session()  # noqa: SLF001
        self.runtime.stop()
        assert self.runtime._lco is not None  # noqa: SLF001
        self.assertTrue(self.runtime._lco.cancel_event.is_set())  # noqa: SLF001


class LcoValidateTests(unittest.TestCase):
    def _report(self, raw: dict):
        store = MagicMock()
        store.rois = {}
        store.collections = {}
        store.events = {"e": _event(raw)}
        return validate_store(store)

    def test_needs_action_or_key(self) -> None:
        report = self._report({"type": "lco"})
        self.assertFalse(report.ok)

    def test_unknown_action(self) -> None:
        report = self._report({"type": "lco", "action": "buy_9"})
        self.assertFalse(report.ok)

    def test_known_action_and_key_ok(self) -> None:
        self.assertTrue(self._report({"type": "lco", "action": "fling_down"}).ok)
        self.assertTrue(self._report({"type": "lco", "key": "W"}).ok)


if __name__ == "__main__":
    unittest.main()
