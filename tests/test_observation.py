"""Observation session writer tests (no live screen capture)."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from idle_lab.models import Rect
from idle_lab.observation.digest import build_observation_digest, write_observation_digest
from idle_lab.observation.session import ObservationController, ObservationPolicy, auto_observation_title
from idle_lab.flight_deck.actions import normalize_action
from idle_lab.hotkeys import InputHooks


def _fake_grab(_rect):
    # Slightly unique per call time so similar-hash skip is deterministic when desired.
    return Image.new("RGB", (64, 48), color=(40, 80, 120))


def _wait_shots(ctrl: ObservationController, minimum: int, timeout: float = 4.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline and ctrl.shot_count < minimum:
        time.sleep(0.05)


class ObservationSessionTests(unittest.TestCase):
    def test_auto_title(self) -> None:
        self.assertTrue(auto_observation_title().startswith("Observation "))

    def test_spam_clicks_coalesce_timeline_and_few_shots(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=100, top=50, right=420, bottom=290)
            ctrl = ObservationController(
                policy=ObservationPolicy(
                    settle_ms=0,
                    burst_gap_ms=80,
                    debounce_down_ms=0,
                    keyframe_min_interval_ms=0,
                    defer_session_start=True,
                    skip_similar=False,
                    max_shots=30,
                    max_pending_frames=4,
                ),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="Spam", anchor_title="Win", anchor_rect=rect)
            for _ in range(20):
                ctrl.handle_button(
                    down=True, button="left", x=200, y=120, anchor_title="Win", anchor_rect=rect
                )
                ctrl.handle_button(
                    down=False, button="left", x=202, y=121, anchor_title="Win", anchor_rect=rect
                )
                time.sleep(0.005)
            time.sleep(0.35)
            _wait_shots(ctrl, 1)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            self.assertLessEqual(summary.shot_count, 4)
            self.assertGreaterEqual(summary.shot_count, 1)
            timeline = (summary.folder / "timeline.jsonl").read_text(encoding="utf-8")
            self.assertIn("pointer_burst", timeline)
            header = json.loads((summary.folder / "observation.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(header["counts"]["clicks"], 15)
            self.assertGreaterEqual(header["counts"]["clicks_coalesced"], 10)
            self.assertTrue((summary.folder / "DIGEST.md").is_file())
            self.assertTrue((summary.folder / "digest.json").is_file())

    def test_debounce_same_locus_downs(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=0, top=0, right=100, bottom=100)
            ctrl = ObservationController(
                policy=ObservationPolicy(
                    debounce_down_ms=200,
                    debounce_locus_px=20,
                    defer_session_start=False,
                    settle_ms=0,
                    burst_gap_ms=50,
                    keyframe_min_interval_ms=0,
                    skip_similar=False,
                ),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="Debounce", anchor_title="W", anchor_rect=rect)
            ctrl.handle_button(down=True, button="left", x=10, y=10, anchor_title="W", anchor_rect=rect)
            ctrl.handle_button(down=False, button="left", x=10, y=10, anchor_title="W", anchor_rect=rect)
            # Immediate re-down at same locus should debounce.
            ctrl.handle_button(down=True, button="left", x=11, y=11, anchor_title="W", anchor_rect=rect)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            header = json.loads((summary.folder / "observation.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(header["counts"]["downs_debounced"], 1)

    def test_semantic_mode_skips_auto_frames(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=0, top=0, right=50, bottom=50)
            ctrl = ObservationController(
                policy=ObservationPolicy(mode="semantic", frames="none", settle_ms=0, burst_gap_ms=50),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="Semantic", anchor_title="W", anchor_rect=rect)
            for _ in range(3):
                ctrl.handle_button(down=True, button="left", x=10, y=10, anchor_title="W", anchor_rect=rect)
                ctrl.handle_button(down=False, button="left", x=10, y=10, anchor_title="W", anchor_rect=rect)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            self.assertEqual(summary.shot_count, 0)
            timeline = (summary.folder / "timeline.jsonl").read_text(encoding="utf-8")
            self.assertTrue("pointer_burst" in timeline or "pointer_up" in timeline)

    def test_drag_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=0, top=0, right=200, bottom=200)
            ctrl = ObservationController(
                policy=ObservationPolicy(
                    settle_ms=0,
                    burst_gap_ms=0,
                    drag_threshold_px=12,
                    keyframe_min_interval_ms=0,
                    skip_similar=False,
                    defer_session_start=False,
                ),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="Drag test", anchor_title="Win", anchor_rect=rect)
            ctrl.handle_button(down=True, button="left", x=10, y=10, anchor_title="Win", anchor_rect=rect)
            ctrl.handle_button(down=False, button="left", x=40, y=10, anchor_title="Win", anchor_rect=rect)
            time.sleep(0.2)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            timeline = (summary.folder / "timeline.jsonl").read_text(encoding="utf-8")
            self.assertIn('"type": "drag"', timeline)

    def test_nav_force_survives_followup_drag(self) -> None:
        """Nav keyframe must not be cancelled when a drag bumps burst_gen mid-settle."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=0, top=0, right=200, bottom=200)
            palette = [(220, 40, 40), (40, 220, 40), (40, 40, 220), (220, 220, 40), (40, 220, 220)]
            idx = {"i": 0}

            def grab(_rect):
                color = palette[idx["i"] % len(palette)]
                idx["i"] += 1
                return Image.new("RGB", (64, 48), color=color)

            ctrl = ObservationController(
                policy=ObservationPolicy(
                    settle_ms=250,
                    burst_gap_ms=50,
                    drag_threshold_px=12,
                    keyframe_min_interval_ms=0,
                    skip_similar=True,
                    defer_session_start=True,
                    nav_ny_min=0.92,
                    max_pending_frames=8,
                ),
                grab_fn=grab,
            )
            ctrl.start(root, title="Nav then drag", anchor_title="Win", anchor_rect=rect)
            # Bottom-tab nav click (ny >= 0.92).
            ctrl.handle_button(down=True, button="left", x=100, y=190, anchor_title="Win", anchor_rect=rect)
            ctrl.handle_button(down=False, button="left", x=100, y=190, anchor_title="Win", anchor_rect=rect)
            # Drag while nav settle is still pending.
            ctrl.handle_button(down=True, button="left", x=80, y=100, anchor_title="Win", anchor_rect=rect)
            ctrl.handle_button(down=False, button="left", x=80, y=40, anchor_title="Win", anchor_rect=rect)
            _wait_shots(ctrl, 3, timeout=5.0)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            timeline = (summary.folder / "timeline.jsonl").read_text(encoding="utf-8")
            self.assertIn('"nav": true', timeline)
            self.assertIn('"type": "drag"', timeline)
            kinds = []
            for line in timeline.splitlines():
                row = json.loads(line)
                if row.get("type") == "keyframe":
                    kinds.append(row.get("kind"))
            self.assertIn("burst", kinds)
            self.assertIn("drag", kinds)
            self.assertGreaterEqual(summary.shot_count, 3)

    def test_anchor_changed_event(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect_a = Rect(left=0, top=0, right=100, bottom=100)
            rect_b = Rect(left=10, top=10, right=110, bottom=110)
            ctrl = ObservationController(
                policy=ObservationPolicy(settle_ms=0, defer_session_start=True, frames="none"),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="Anchor", anchor_title="A", anchor_rect=rect_a)
            ctrl.handle_move(20, 20, anchor_title="B", anchor_rect=rect_b)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            timeline = (summary.folder / "timeline.jsonl").read_text(encoding="utf-8")
            self.assertIn('"type": "anchor_changed"', timeline)

    def test_rename_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=0, top=0, right=50, bottom=50)
            ctrl = ObservationController(
                policy=ObservationPolicy(settle_ms=0, defer_session_start=False, skip_similar=False),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="Observation temp", anchor_title="W", anchor_rect=rect)
            time.sleep(0.15)
            summary = ctrl.stop(reason="operator")
            assert summary is not None
            renamed = ctrl.rename("Buy order Attack")
            self.assertTrue(renamed.exists())
            self.assertIn("buy-order-attack", renamed.name)
            digest = build_observation_digest(renamed)
            self.assertEqual(digest["title"], "Buy order Attack")
            self.assertIn("analysis_hint", digest)


class ObservationLiveControlNoteTests(unittest.TestCase):
    def test_note_live_control_timeline_and_forced_shots(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rect = Rect(left=10, top=20, right=210, bottom=320)
            ctrl = ObservationController(
                policy=ObservationPolicy(
                    settle_ms=0,
                    defer_session_start=True,
                    skip_similar=False,
                    max_shots=30,
                    max_pending_frames=8,
                ),
                grab_fn=_fake_grab,
            )
            ctrl.start(root, title="live-control-troubleshoot-test", anchor_title="Win", anchor_rect=rect)
            ctrl.note_live_control(
                action="page_down",
                phase="before",
                detail="page down",
                meta={"direction": "down", "page_fraction": 0.3},
                anchor_title="Win",
                anchor_rect=rect,
            )
            ctrl.note_live_control(
                action="page_down",
                phase="after",
                detail="page down snapped",
                meta={"snapped": True, "slot_count": 6},
                anchor_title="Win",
                anchor_rect=rect,
            )
            _wait_shots(ctrl, 2)
            summary = ctrl.stop(reason="live-control-exit")
            assert summary is not None
            self.assertGreaterEqual(summary.shot_count, 2)
            timeline = (summary.folder / "timeline.jsonl").read_text(encoding="utf-8")
            self.assertIn('"type": "live_control_action"', timeline)
            self.assertIn("page_down", timeline)
            header = json.loads((summary.folder / "observation.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(header["counts"]["live_control_actions"], 2)
            digest = build_observation_digest(summary.folder)
            action_types = {row.get("type") for row in digest.get("actions") or []}
            self.assertIn("live_control_action", action_types)


class ObservationHookQueueTests(unittest.TestCase):
    def test_observation_move_coalesces_under_pressure(self) -> None:
        hooks = InputHooks()
        for _ in range(80):
            hooks.events.put(("noise",))
        hooks._put_observation(("observation_move", 1, 2))
        hooks._put_observation(("observation_move", 3, 4))
        self.assertEqual(hooks._obs_latest_move, (3, 4))
        drained = hooks.drain()
        self.assertIn(("observation_move", 3, 4), drained)


class ObservationActionTests(unittest.TestCase):
    def test_aliases(self) -> None:
        self.assertEqual(normalize_action({"type": "observe_start"})["type"], "observation_start")
        self.assertEqual(normalize_action({"type": "observe_shot"})["type"], "observation_mark")
        self.assertEqual(normalize_action({"type": "observe_end"})["type"], "observation_end")


if __name__ == "__main__":
    unittest.main()
