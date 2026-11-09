"""Doctor window resolution with mocked enum."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.harness.context import load_lab_context
from idle_lab.harness.doctor import find_target_window, run_doctor
from idle_lab.models import Rect


class FindTargetWindowTests(unittest.TestCase):
    def test_prefers_last_anchor_exact(self) -> None:
        from idle_lab.harness.context import TargetProfile

        target = TargetProfile(
            id="tower",
            label="The Tower",
            anchor_title_substrings=("BlueStacks",),
            prefer_last_anchor=True,
        )

        def enum_windows():
            return [
                (1, "Other", 10, True, False),
                (2, "BlueStacks App Player", 11, True, False),
                (3, "MySavedAnchor", 12, True, False),
            ]

        candidate, mode, _ = find_target_window(
            target,
            last_anchor_title="MySavedAnchor",
            our_pid=999,
            enum_windows=enum_windows,
        )
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.hwnd, 3)
        self.assertEqual(mode, "last_anchor_exact")

    def test_falls_back_to_substring(self) -> None:
        from idle_lab.harness.context import TargetProfile

        target = TargetProfile(
            id="tower",
            label="The Tower",
            anchor_title_substrings=("BlueStacks",),
            prefer_last_anchor=True,
        )

        def enum_windows():
            return [
                (1, "Chrome", 10, True, False),
                (2, "BlueStacks App Player", 11, True, False),
            ]

        candidate, mode, _ = find_target_window(
            target,
            last_anchor_title="GoneWindow",
            our_pid=999,
            enum_windows=enum_windows,
        )
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.hwnd, 2)
        self.assertEqual(mode, "substring:BlueStacks")

    def test_ambiguous_substring_returns_none(self) -> None:
        from idle_lab.harness.context import TargetProfile

        target = TargetProfile(
            id="tower",
            label="The Tower",
            anchor_title_substrings=("BlueStacks",),
            prefer_last_anchor=False,
        )

        def enum_windows():
            return [
                (1, "BlueStacks A", 10, True, False),
                (2, "BlueStacks B", 11, True, False),
            ]

        candidate, mode, _ = find_target_window(
            target,
            our_pid=999,
            enum_windows=enum_windows,
        )
        self.assertIsNone(candidate)
        self.assertIsNone(mode)


class RunDoctorTests(unittest.TestCase):
    def test_doctor_ok_with_fake_windows(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lab-context.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "active_target": "tower",
                        "targets": {
                            "tower": {
                                "label": "The Tower",
                                "anchor_title_substrings": ["BlueStacks"],
                                "prefer_last_anchor": True,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "settings.json").write_text("{}", encoding="utf-8")
            ctx = load_lab_context(root)

            def enum_windows():
                return [(42, "BlueStacks App Player", 7, True, False)]

            def get_rect(hwnd: int) -> Rect | None:
                self.assertEqual(hwnd, 42)
                return Rect(0, 0, 100, 200)

            result = run_doctor(
                root=root,
                context=ctx,
                enum_windows=enum_windows,
                get_rect=get_rect,
            )
            self.assertTrue(result.ok)
            self.assertEqual(result.hwnd, 42)
            self.assertEqual(result.rect["width"], 100)

    def test_doctor_missing_window(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "lab-context.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "active_target": "tower",
                        "targets": {
                            "tower": {
                                "label": "The Tower",
                                "anchor_title_substrings": ["BlueStacks"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "settings.json").write_text("{}", encoding="utf-8")
            ctx = load_lab_context(root)
            result = run_doctor(
                root=root,
                context=ctx,
                enum_windows=lambda: [(1, "Notepad", 3, True, False)],
                get_rect=lambda _hwnd: None,
            )
            self.assertFalse(result.ok)
            self.assertIn("Open The Tower", result.hint)


if __name__ == "__main__":
    unittest.main()
