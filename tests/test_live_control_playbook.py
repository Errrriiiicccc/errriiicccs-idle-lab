"""Live Control Overlay playbook + controller smoke (no live window)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from idle_lab.live_control.buy_detect import BuyGridDetection, DetectedBuySlot
from idle_lab.live_control.controller import LiveControlController
from idle_lab.live_control.objects import default_object_map_path, load_object_map
from idle_lab.live_control.overlay import LiveControlOverlay, _Box, _DescribeLayout, _MARKER_R
from idle_lab.live_control.playbook import default_playbook_path, load_playbook
from idle_lab.models import Rect
from idle_lab.presets import project_root


class LiveControlPlaybookTests(unittest.TestCase):
    def test_loads_tower_main_gameplay(self) -> None:
        path = default_playbook_path(project_root())
        self.assertTrue(path.is_file(), msg=f"missing {path}")
        self.assertTrue(str(path).endswith("tower_main_gameplay.objects.json"))
        pb = load_playbook(path)
        self.assertEqual(pb.surface, "main_gameplay")
        self.assertIsNotNone(pb.object_map)
        self.assertEqual(pb.action_for_token("Q"), "tab_attack")
        self.assertEqual(pb.action_for_token("1"), "buy_1")
        self.assertEqual(pb.action_for_token("B"), "refresh")
        self.assertEqual(pb.action_for_token("F"), "scroll_down")
        self.assertEqual(pb.action_for_token("T"), "fling_up")
        self.assertEqual(pb.action_for_token("G"), "fling_down")
        self.assertEqual(pb.action_for_token("D"), "describe")
        self.assertEqual(len(pb.buy_slots("attack")), 6)
        self.assertEqual(pb.buy_slots("attack")[0].label, "Damage")
        self.assertIn("defense", pb.tabs)
        self.assertEqual(int(pb.scroll.get("rows_per_key") or 0), 1)
        self.assertNotIn("page_rows", pb.scroll)

    def test_object_map_containment_and_effects(self) -> None:
        path = default_object_map_path(project_root())
        omap = load_object_map(path)
        attack = omap.tab_button("attack")
        assert attack is not None
        self.assertEqual(attack.opens_panel(), "panel.attack")
        self.assertTrue(omap.no_retap_if_active("attack"))
        listing = omap.scroll_list_for_tab("attack")
        assert listing is not None
        self.assertEqual(listing.parent, "panel.attack")
        buy = omap.buy_button("attack", 1)
        assert buy is not None
        self.assertEqual(buy.label, "Damage")
        world = buy.effects.get("world") or []
        self.assertTrue(any(e.get("type") == "spend" for e in world if isinstance(e, dict)))
        shim = project_root() / "automations" / "playbooks" / "tower_main_gameplay.json"
        pb = load_playbook(shim)
        self.assertIsNotNone(pb.object_map)
        self.assertEqual(pb.buy_slots("defense")[0].label, "Health")

    def test_handle_token_ignored_when_inactive(self) -> None:
        root = MagicMock()
        overlay = MagicMock(spec=LiveControlOverlay)
        ctrl = LiveControlController(
            overlay=overlay,
            project_root=project_root(),
            get_anchor=lambda: (None, None, None),
        )
        self.assertFalse(ctrl.handle_token("Q"))


class LiveControlFlightDeckActionTests(unittest.TestCase):
    def test_live_control_actions_normalize(self) -> None:
        from idle_lab.flight_deck.actions import normalize_action

        self.assertEqual(normalize_action({"type": "live_control_enter"})["type"], "live_control_enter")
        self.assertEqual(
            normalize_action({"type": "live_control_enter_troubleshoot"})["type"],
            "live_control_enter_troubleshoot",
        )
        self.assertEqual(normalize_action({"type": "live_control_exit"})["type"], "live_control_exit")
        self.assertEqual(normalize_action({"type": "live_control_toggle"})["type"], "live_control_toggle")
        # Legacy Manual action ids still normalize.
        self.assertEqual(normalize_action({"type": "manual_enter"})["type"], "live_control_enter")
        self.assertEqual(normalize_action({"type": "manual_exit"})["type"], "live_control_exit")

    def test_evidence_callback_fires_when_enabled(self) -> None:
        notes: list[dict] = []

        def on_evidence(**kwargs) -> None:
            notes.append(kwargs)

        ctrl = LiveControlController(
            overlay=MagicMock(spec=LiveControlOverlay),
            project_root=project_root(),
            get_anchor=lambda: (None, None, None),
            on_evidence=on_evidence,
        )
        ctrl.active = True
        ctrl.evidence = True
        ctrl._emit_evidence("scroll_down", "before", detail="row down", meta={"direction": "down"})
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["action"], "scroll_down")
        self.assertEqual(notes[0]["phase"], "before")
        ctrl.evidence = False
        ctrl._emit_evidence("scroll_down", "after", detail="ignored")
        self.assertEqual(len(notes), 1)


class LiveControlScrollModelTests(unittest.TestCase):
    def _controller(self) -> LiveControlController:
        ctrl = LiveControlController(
            overlay=MagicMock(spec=LiveControlOverlay),
            project_root=project_root(),
            get_anchor=lambda: ("BlueStacks", 42, Rect(0, 0, 593, 1028)),
        )
        ctrl.active = True
        ctrl.playbook = load_playbook(default_playbook_path(project_root()))
        ctrl.panel_open = True
        ctrl.tab = "attack"
        return ctrl

    def test_scroll_does_one_row_drag_then_relayout(self) -> None:
        ctrl = self._controller()
        detection = BuyGridDetection(
            snapped=False,
            slots=[DetectedBuySlot(1, 0.32, 0.70), DetectedBuySlot(2, 0.72, 0.70)],
            reason="clipped first row gap=0.020",
            row_nys=(0.70,),
            header_ny=0.68,
        )

        def fake_relayout(_rect, *, context: str):
            ctrl._apply_detection(detection, context=context)
            return detection

        with (
            patch("idle_lab.live_control.controller.drag_list") as drag,
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout) as relayout,
            patch.object(ctrl, "_repaint"),
        ):
            ctrl._do_scroll("down", mode="step")
        self.assertEqual(drag.call_count, 1)
        self.assertEqual(drag.call_args.kwargs["direction"], "down")
        self.assertAlmostEqual(drag.call_args.kwargs["drag_fraction"], 0.15)
        relayout.assert_called_once()
        self.assertFalse(ctrl.aligned)
        self.assertEqual(len(ctrl.live_slots), 2)

    def test_fling_uses_momentum_swipe(self) -> None:
        ctrl = self._controller()
        detection = BuyGridDetection(
            snapped=True,
            slots=[DetectedBuySlot(1, 0.32, 0.74)],
            reason="snapped",
            row_nys=(0.74,),
            header_ny=0.66,
        )

        def fake_relayout(_rect, *, context: str):
            ctrl._apply_detection(detection, context=context)
            return detection

        with (
            patch("idle_lab.live_control.controller.fling_list") as fling,
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout),
            patch.object(ctrl, "_repaint"),
        ):
            ctrl._do_scroll("up", mode="fling")
        self.assertEqual(fling.call_count, 1)
        self.assertEqual(fling.call_args.kwargs["direction"], "up")
        self.assertGreaterEqual(fling.call_args.kwargs["drag_fraction"], 0.25)

    def test_scroll_keys_dispatch_step_not_fling(self) -> None:
        ctrl = self._controller()
        with (
            patch.object(ctrl, "_do_scroll") as scroll,
            patch.object(ctrl, "_repaint"),
        ):
            self.assertTrue(ctrl.handle_key("F", phase="down"))
            scroll.assert_called_once_with("down", mode="step")

    def test_fling_keys_dispatch_fling(self) -> None:
        ctrl = self._controller()
        with (
            patch.object(ctrl, "_do_scroll") as scroll,
            patch.object(ctrl, "_repaint"),
        ):
            self.assertTrue(ctrl.handle_key("G", phase="down"))
            scroll.assert_called_once_with("down", mode="fling")

    def test_scroll_step_drag_fraction_from_object_map(self) -> None:
        ctrl = self._controller()
        self.assertAlmostEqual(float(ctrl._scroll_params("attack").get("drag_fraction")), 0.15)
        self.assertGreaterEqual(int(ctrl._scroll_params("attack").get("drag_steps") or 0), 8)

    def test_buy_still_fires_when_unaligned(self) -> None:
        ctrl = self._controller()
        ctrl.aligned = False
        ctrl.live_slots = (DetectedBuySlot(1, 0.32, 0.74),)
        with (
            patch.object(ctrl, "_click") as click,
            patch.object(ctrl, "_repaint"),
        ):
            ctrl._do_buy(1)
        click.assert_called_once()
        self.assertAlmostEqual(click.call_args.kwargs["nx"], 0.32)
        self.assertAlmostEqual(click.call_args.kwargs["ny"], 0.74)

    def test_d_hold_shows_descriptors_release_clears(self) -> None:
        noted: list[bool] = []
        ctrl = self._controller()
        ctrl.on_legend_change = noted.append
        with patch.object(ctrl, "_repaint") as repaint:
            self.assertTrue(ctrl.handle_key("D", phase="down"))
        self.assertTrue(ctrl.show_descriptors)
        self.assertEqual(noted, [True])
        repaint.assert_called_once()
        with patch.object(ctrl, "_repaint") as repaint_up:
            self.assertTrue(ctrl.handle_key("D", phase="up"))
        self.assertFalse(ctrl.show_descriptors)
        self.assertEqual(noted, [True, False])
        repaint_up.assert_called_once()
        # Second down while already clear is a no-op until held again.
        with patch.object(ctrl, "_repaint") as repaint_again:
            self.assertTrue(ctrl.handle_key("D", phase="down"))
        self.assertTrue(ctrl.show_descriptors)
        repaint_again.assert_called_once()

    def test_pause_grays_out_and_blocks_actions(self) -> None:
        pauses: list[bool] = []
        ctrl = self._controller()
        ctrl.on_pause_change = pauses.append
        with patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.toggle_pause())
        self.assertTrue(ctrl.paused)
        self.assertEqual(pauses, [True])
        with patch.object(ctrl, "_do_scroll") as scroll:
            self.assertTrue(ctrl.handle_key("F", phase="down"))
            scroll.assert_not_called()
        with patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.toggle_pause())
        self.assertFalse(ctrl.paused)
        self.assertEqual(pauses, [True, False])

    def test_scroll_badges_cluster_on_list_viewport(self) -> None:
        ctrl = self._controller()
        scroll = ctrl.playbook.scroll if ctrl.playbook else {}
        fling_up = float(scroll.get("fling_up_badge_ny") or 0)
        step_up = float(scroll.get("up_badge_ny") or 0)
        step_down = float(scroll.get("down_badge_ny") or 0)
        fling_down = float(scroll.get("fling_down_badge_ny") or 0)
        self.assertLess(fling_up, step_up)
        self.assertLess(step_up, step_down)
        self.assertLess(step_down, fling_down)
        self.assertLessEqual(step_up - fling_up, 0.05)
        self.assertLessEqual(fling_down - step_down, 0.05)
        self.assertLessEqual(fling_up, 0.63)


class DescribeLayoutTests(unittest.TestCase):
    def test_label_pathfinds_around_blocking_icon(self) -> None:
        """Tab-mid attach must not park the label box on a buy icon sitting above it."""

        layout = _DescribeLayout(bounds=_Box(0, 0, 500, 900))
        attach = (200.0, 820.0)
        layout.add_circle(*attach, _MARKER_R)
        blocker = (200.0, 760.0)  # straight-up buy-5 style collision
        layout.add_circle(*blocker, _MARKER_R)
        layout.add_circle(140.0, 760.0, _MARKER_R)
        layout.add_circle(260.0, 760.0, _MARKER_R)
        half_w, half_h = 72.0, 12.0
        placed = layout.place(attach, half_w, half_h, prefer="up")
        self.assertIsNotNone(placed)
        assert placed is not None
        cx, cy, _mode = placed
        box = _Box(cx - half_w, cy - half_h, cx + half_w, cy + half_h)
        self.assertFalse(box.contains_point(*blocker))
        self.assertFalse(
            box.overlaps(
                _Box(
                    blocker[0] - _MARKER_R - 8,
                    blocker[1] - _MARKER_R - 8,
                    blocker[0] + _MARKER_R + 8,
                    blocker[1] + _MARKER_R + 8,
                )
            )
        )
        self.assertLess(cy, attach[1])


if __name__ == "__main__":
    unittest.main()
