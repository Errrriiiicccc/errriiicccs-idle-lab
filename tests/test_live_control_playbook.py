"""Live Control Overlay playbook + controller smoke (no live window)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from idle_lab.live_control.buy_detect import BuyGridDetection, DetectedBuySlot
from idle_lab.live_control.controller import LiveControlController
from idle_lab.live_control.objects import default_object_map_path, load_object_map
from idle_lab.live_control.overlay import LiveControlOverlay, _Box, _DescribeLayout, _MARKER_R
from idle_lab.live_control.playbook import (
    FIRE_MODE_SINGLE,
    FIRE_MODE_SPAM,
    FIRE_MODE_TOGGLE,
    default_playbook_path,
    fire_mode_for,
    load_playbook,
)
from idle_lab.models import Rect
from idle_lab.presets import project_root


class LiveControlPlaybookTests(unittest.TestCase):
    def test_fire_modes(self) -> None:
        self.assertEqual(fire_mode_for("buy_3"), FIRE_MODE_SPAM)
        self.assertEqual(fire_mode_for("scroll_down"), FIRE_MODE_SPAM)
        self.assertEqual(fire_mode_for("fling_up"), FIRE_MODE_SPAM)
        self.assertEqual(fire_mode_for("claim_gem"), FIRE_MODE_SPAM)
        self.assertEqual(fire_mode_for("tab_defense"), FIRE_MODE_SINGLE)
        self.assertEqual(fire_mode_for("stat_collect"), FIRE_MODE_SINGLE)
        self.assertEqual(fire_mode_for("refresh"), FIRE_MODE_SINGLE)
        self.assertEqual(fire_mode_for("routine_health_damage_claim"), FIRE_MODE_TOGGLE)

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
        self.assertEqual(pb.action_for_token("C"), "claim_gem")
        self.assertEqual(pb.action_for_token("A"), "routine_health_damage_claim")
        self.assertIsNone(pb.action_for_token("Y"))
        self.assertIsNone(pb.action_for_token("H"))
        self.assertEqual(len(pb.routines), 1)
        self.assertEqual(pb.routines[0].action, "routine_health_damage_claim")
        self.assertEqual(pb.routines[0].steps[0], "tab_defense")
        self.assertAlmostEqual(pb.routines[0].nx, 0.08, places=2)
        self.assertAlmostEqual(float(pb.chrome.get("claim_badge_nx") or 0), 0.20, places=2)
        self.assertAlmostEqual(float(pb.chrome.get("claim_badge_ny") or 0), 0.50, places=2)
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
        self.assertEqual(
            normalize_action({"type": "live_control_console_toggle"})["type"],
            "live_control_console_toggle",
        )
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

        def fake_relayout(_rect, *, context: str, identity: str = "ocr"):
            ctrl._apply_detection(detection, context=context)
            return detection

        with (
            patch("idle_lab.live_control.controller.drag_list") as drag,
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout) as relayout,
            patch.object(ctrl, "_sleep_ms", return_value=False),
            patch.object(ctrl, "_repaint"),
        ):
            ctrl._do_scroll("down", mode="step")
        self.assertEqual(drag.call_count, 1)
        self.assertEqual(drag.call_args.kwargs["direction"], "down")
        self.assertAlmostEqual(drag.call_args.kwargs["drag_fraction"], 0.10)
        relayout.assert_called_once()
        self.assertFalse(ctrl.aligned)
        self.assertEqual(len(ctrl.live_slots), 2)

    def test_routine_runs_sequence_inline(self) -> None:
        ctrl = self._controller()
        fired: list[str] = []
        with (
            patch.object(ctrl, "_dispatch", side_effect=lambda action: fired.append(action)),
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence"),
        ):
            ctrl._do_routine("routine_health_damage_claim")
        self.assertEqual(
            fired,
            ["tab_defense", "buy_1", "tab_attack", "buy_1", "tab_defense", "claim_gem"],
        )

    def test_a_key_toggles_routine_loop(self) -> None:
        ctrl = self._controller()
        posts: list[tuple] = []
        ctrl.post_event = posts.append
        with (
            patch.object(ctrl, "_do_routine"),
            patch.object(ctrl, "_repaint"),
        ):
            self.assertTrue(ctrl.handle_key("A", phase="down"))
            self.assertEqual(ctrl._toggled_action, "routine_health_damage_claim")
            self.assertTrue(any(item[0] == "live_control_repeat" for item in posts))
            posts.clear()
            self.assertTrue(ctrl.handle_key("A", phase="up"))
            self.assertEqual(ctrl._toggled_action, "routine_health_damage_claim")
            self.assertTrue(ctrl.handle_key("A", phase="down"))
            self.assertIsNone(ctrl._toggled_action)

    def test_spam_hold_repeats_buy_single_does_not(self) -> None:
        ctrl = self._controller()
        with patch.object(ctrl, "_do_buy") as buy, patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("1", phase="down"))
            self.assertIn("buy_1", ctrl._held_actions)
            buy.assert_called()
            buy.reset_mock()
            ctrl.continue_repeat("buy_1")
            buy.assert_called()
            self.assertTrue(ctrl.handle_key("1", phase="up"))
            self.assertNotIn("buy_1", ctrl._held_actions)

        with patch.object(ctrl, "_do_tab") as tab, patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("Q", phase="down"))
            tab.assert_called_once()
            self.assertEqual(ctrl._held_actions, [])
            self.assertTrue(ctrl.handle_key("Q", phase="up"))
            self.assertEqual(tab.call_count, 1)

    def test_keys_queue_while_busy(self) -> None:
        ctrl = self._controller()
        ctrl._busy = True
        with patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("1", phase="down"))
            self.assertTrue(ctrl.handle_key("W", phase="down"))
        self.assertEqual(ctrl._action_queue, ["buy_1", "tab_defense"])
        self.assertEqual(ctrl._visible_queue(), ("buy_1", "tab_defense"))

    def test_scroll_settle_is_short(self) -> None:
        ctrl = self._controller()
        scroll = ctrl._scroll_params("attack")
        self.assertLessEqual(int(scroll.get("settle_ms") or 0), 100)
        self.assertLessEqual(int(scroll.get("fling_settle_ms") or 0), 100)
        self.assertGreaterEqual(int(scroll.get("settle_ms") or 0), 30)
        self.assertGreaterEqual(int(scroll.get("detect_settle_ms") or 0), 150)

    def test_async_action_finishes_via_done_event(self) -> None:
        posted: list[tuple] = []
        tokens: list[str | None] = []
        ctrl = self._controller()
        ctrl.post_event = posted.append
        ctrl.async_actions = True
        ctrl.on_toggle_token = tokens.append
        with patch.object(ctrl, "_do_routine") as routine, patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("A", phase="down"))
            self.assertEqual(tokens[-1], "A")
            self.assertTrue(ctrl._busy)
            self.assertIsNotNone(ctrl._worker)
            assert ctrl._worker is not None
            ctrl._worker.join(timeout=2.0)
            self.assertFalse(ctrl._worker.is_alive())
            routine.assert_called_once()
            self.assertEqual(posted[0][0], "live_control_done")
            ctrl.finish_action(str(posted[0][1]), repeat=posted[0][2], errors=posted[0][3])
            self.assertFalse(ctrl._busy)
            self.assertEqual(posted[1][0], "live_control_repeat")

    def test_toggle_off_sets_cancel_immediately(self) -> None:
        ctrl = self._controller()
        tokens: list[str | None] = []
        ctrl.on_toggle_token = tokens.append
        with patch.object(ctrl, "_do_routine"), patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("A", phase="down"))
            self.assertEqual(ctrl._toggled_action, "routine_health_damage_claim")
            self.assertEqual(tokens[-1], "A")
            self.assertTrue(ctrl.handle_key("A", phase="down"))
        self.assertIsNone(ctrl._toggled_action)
        self.assertTrue(ctrl.cancel_event.is_set())
        self.assertIsNone(tokens[-1])

    def test_enqueue_does_not_clear_cancel(self) -> None:
        ctrl = self._controller()
        ctrl._busy = True
        ctrl.cancel_event.set()
        with patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("1", phase="down"))
        self.assertTrue(ctrl.cancel_event.is_set())
        self.assertEqual(ctrl._action_queue, ["buy_1"])

    def test_tab_switch_homes_with_fling(self) -> None:
        ctrl = self._controller()
        ctrl.tab = "defense"
        detection = BuyGridDetection(
            snapped=True,
            slots=[DetectedBuySlot(1, 0.32, 0.74)],
            reason="snapped",
            row_nys=(0.74,),
            header_ny=0.66,
        )
        with (
            patch("idle_lab.live_control.controller.fling_list") as fling,
            patch("idle_lab.live_control.controller.click_normalized"),
            patch.object(ctrl, "_relayout_from_screen", return_value=detection),
            patch.object(ctrl, "_sleep_ms", return_value=False),
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence"),
        ):
            ctrl._do_tab("attack")
        self.assertEqual(fling.call_count, 1)
        self.assertEqual(fling.call_args.kwargs["direction"], "up")
        self.assertGreaterEqual(fling.call_args.kwargs["drag_fraction"], 0.25)

    def test_fling_uses_momentum_swipe(self) -> None:
        ctrl = self._controller()
        detection = BuyGridDetection(
            snapped=True,
            slots=[DetectedBuySlot(1, 0.32, 0.74)],
            reason="snapped",
            row_nys=(0.74,),
            header_ny=0.66,
        )

        def fake_relayout(_rect, *, context: str, identity: str = "ocr"):
            ctrl._apply_detection(detection, context=context)
            if identity == "home":
                ctrl._home_identity(reason=context)
            return detection

        with (
            patch("idle_lab.live_control.controller.fling_list") as fling,
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout),
            patch.object(ctrl, "_sleep_ms", return_value=False),
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
        self.assertAlmostEqual(float(ctrl._scroll_params("attack").get("drag_fraction")), 0.10)
        self.assertGreaterEqual(int(ctrl._scroll_params("attack").get("drag_steps") or 0), 8)

    def test_buy_still_fires_when_unaligned(self) -> None:
        ctrl = self._controller()
        ctrl.aligned = False
        ctrl.live_slots = (DetectedBuySlot(1, 0.32, 0.74),)
        with (
            patch.object(ctrl, "_click") as click,
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence") as evidence,
        ):
            ctrl._do_buy(1)
        click.assert_called_once()
        self.assertAlmostEqual(click.call_args.kwargs["nx"], 0.32)
        self.assertAlmostEqual(click.call_args.kwargs["ny"], 0.74)
        # Unknown identity must not pretend this is still page-1 Damage.
        self.assertEqual(evidence.call_args.kwargs["detail"], "?")
        self.assertIsNone(evidence.call_args.kwargs["meta"].get("object_id"))

    def test_identity_homes_on_tab_via_ocr_or_page_fallback(self) -> None:
        ctrl = self._controller()
        ctrl.tab = "defense"
        detection = BuyGridDetection(
            snapped=True,
            slots=[
                DetectedBuySlot(1, 0.32, 0.74),
                DetectedBuySlot(2, 0.72, 0.74),
                DetectedBuySlot(3, 0.32, 0.83),
                DetectedBuySlot(4, 0.72, 0.83),
                DetectedBuySlot(5, 0.32, 0.92),
                DetectedBuySlot(6, 0.72, 0.92),
            ],
            reason="snapped",
            row_nys=(0.74, 0.83, 0.92),
            header_ny=0.66,
        )

        def fake_relayout(_rect, *, context: str, identity: str = "ocr"):
            ctrl._apply_detection(detection, context=context)
            if identity == "home":
                ctrl._home_identity(reason=context)
            else:
                ctrl._forget_identity(context)
            return detection

        with (
            patch("idle_lab.live_control.controller.fling_list"),
            patch("idle_lab.live_control.controller.click_normalized"),
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout),
            patch.object(ctrl, "_sleep_ms", return_value=False),
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence"),
        ):
            ctrl._do_tab("attack")
        self.assertTrue(ctrl.identity.known)
        self.assertEqual(ctrl.identity.label_for(1), "Damage")
        self.assertEqual(ctrl.identity.label_for(6), "Dmg/Meter")

    def test_scroll_identity_follows_ocr_not_offset_math(self) -> None:
        """Overshoot scroll: OCR sees Thorn under key 1, not Defense % from +1 row math."""

        ctrl = self._controller()
        ctrl.tab = "defense"
        ctrl.live_slots = (
            DetectedBuySlot(1, 0.32, 0.74),
            DetectedBuySlot(2, 0.72, 0.74),
            DetectedBuySlot(3, 0.32, 0.83),
            DetectedBuySlot(4, 0.72, 0.83),
        )
        ctrl.aligned = True
        ctrl._home_identity(reason="test-top")
        self.assertEqual(ctrl.identity.label_for(1), "Health")

        detection = BuyGridDetection(
            snapped=True,
            slots=list(ctrl.live_slots),
            reason="snapped",
            row_nys=(0.74, 0.83),
            header_ny=0.66,
        )

        def fake_relayout(_rect, *, context: str, identity: str = "ocr"):
            ctrl._apply_detection(detection, context=context)
            # Pretend OCR read the cards that actually landed (past scroll-math expectation).
            from idle_lab.live_control.buy_identity import bind_from_slot_texts

            ctrl.identity = bind_from_slot_texts(
                ctrl._catalog(),
                {
                    1: "Thorn Damage",
                    2: "Lifesteal",
                    3: "Knockback Chance",
                    4: "Knockback Force",
                },
                slot_count=6,
            )
            return detection

        with (
            patch("idle_lab.live_control.controller.drag_list"),
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout),
            patch.object(ctrl, "_sleep_ms", return_value=False),
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence"),
        ):
            ctrl._do_scroll("down", mode="step")
        self.assertTrue(ctrl.identity.known)
        self.assertEqual(ctrl.identity.label_for(1), "Thorn")
        self.assertEqual(ctrl.identity.label_for(2), "Lifesteal")
        self.assertNotEqual(ctrl.identity.label_for(1), "Defense %")

    def test_step_scroll_ocr_miss_stays_unknown(self) -> None:
        ctrl = self._controller()
        ctrl._forget_identity("test")
        detection = BuyGridDetection(
            snapped=True,
            slots=[DetectedBuySlot(1, 0.32, 0.74), DetectedBuySlot(2, 0.72, 0.74)],
            reason="snapped",
            row_nys=(0.74,),
            header_ny=0.66,
        )

        def fake_relayout(_rect, *, context: str, identity: str = "ocr"):
            ctrl._apply_detection(detection, context=context)
            ctrl._forget_identity("ocr-no-hits")
            return detection

        with (
            patch("idle_lab.live_control.controller.drag_list"),
            patch.object(ctrl, "_relayout_from_screen", side_effect=fake_relayout),
            patch.object(ctrl, "_sleep_ms", return_value=False),
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence"),
        ):
            ctrl._do_scroll("down", mode="step")
        self.assertFalse(ctrl.identity.known)
        self.assertEqual(ctrl.identity.label_for(1), "?")

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

    def test_hold_scroll_queues_repeat_until_release(self) -> None:
        posted: list[tuple] = []
        ctrl = self._controller()
        ctrl.post_event = posted.append
        with patch.object(ctrl, "_do_scroll") as scroll, patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("F", phase="down"))
            scroll.assert_called_once_with("down", mode="step")
            self.assertEqual(posted, [("live_control_repeat", "scroll_down")])
            posted.clear()
            ctrl.continue_repeat("scroll_down")
            self.assertEqual(scroll.call_count, 2)
            self.assertEqual(posted, [("live_control_repeat", "scroll_down")])
            ctrl.handle_key("F", phase="up")
            posted.clear()
            ctrl.continue_repeat("scroll_down")
            self.assertEqual(scroll.call_count, 2)
            self.assertEqual(posted, [])

    def test_stat_collect_is_not_hold_repeatable(self) -> None:
        posted: list[tuple] = []
        ctrl = self._controller()
        ctrl.post_event = posted.append
        with patch.object(ctrl, "_do_stat_collect") as stat, patch.object(ctrl, "_repaint"):
            self.assertTrue(ctrl.handle_key("V", phase="down"))
            stat.assert_called_once()
        self.assertEqual(posted, [])
        self.assertEqual(ctrl._held_actions, [])

    def test_pause_and_exit_interrupt_held_work(self) -> None:
        ctrl = self._controller()
        ctrl._held_actions.append("scroll_down")
        with patch.object(ctrl, "_repaint"):
            ctrl.toggle_pause()
        self.assertTrue(ctrl.cancel_event.is_set())
        self.assertEqual(ctrl._held_actions, [])
        ctrl.cancel_event.clear()
        ctrl.paused = False
        ctrl._held_actions.append("buy_1")
        with patch.object(ctrl.overlay, "hide"):
            ctrl.exit(reason="test")
        self.assertTrue(ctrl.cancel_event.is_set())
        self.assertEqual(ctrl._held_actions, [])

    def test_scroll_passes_cancel_event_to_drag(self) -> None:
        ctrl = self._controller()
        with (
            patch("idle_lab.live_control.controller.drag_list") as drag,
            patch.object(
                ctrl,
                "_relayout_from_screen",
                return_value=BuyGridDetection(True, [], "ok", (), None),
            ),
            patch.object(ctrl, "_sleep_ms", return_value=False),
            patch.object(ctrl, "_repaint"),
            patch.object(ctrl, "_emit_evidence"),
        ):
            ctrl._do_scroll("down", mode="step")
        self.assertIs(drag.call_args.kwargs.get("stop"), ctrl.cancel_event)

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
