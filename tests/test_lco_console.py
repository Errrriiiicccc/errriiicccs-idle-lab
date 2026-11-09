"""LCO console session + verbosity helpers + user comments."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from idle_lab.live_control.console import (
    ConsoleSession,
    next_verbosity,
    normalize_verbosity,
)
from idle_lab.live_control.playbook import default_playbook_path, load_playbook
from idle_lab.presets import project_root
from idle_lab.settings_store import load_settings, save_settings
from idle_lab.models import Settings


class ConsoleHelpersTests(unittest.TestCase):
    def test_verbosity_cycle(self) -> None:
        self.assertEqual(normalize_verbosity("nope"), "results")
        self.assertEqual(next_verbosity("events"), "results")
        self.assertEqual(next_verbosity("results"), "process")
        self.assertEqual(next_verbosity("process"), "events")


class ConsoleSessionTests(unittest.TestCase):
    def test_flush_on_stop_writes_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            console = ConsoleSession(project_root=root, enabled=True, verbosity="process")
            folder = console.start_run()
            assert folder is not None
            console.event("pressed buy_1")
            console.result("buy_1 → Damage")
            console.process("ocr slot 1 score=0.9")
            path = console.stop_run(reason="test")
            assert path is not None
            text = path.read_text(encoding="utf-8")
            self.assertIn("[events] pressed buy_1", text)
            self.assertIn("[results] buy_1 → Damage", text)
            self.assertIn("[process] ocr slot 1", text)
            # Dump always keeps timestamps.
            self.assertRegex(text, r"\d{2}:\d{2}:\d{2} \[events\]")

    def test_events_verbosity_hides_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            console = ConsoleSession(project_root=Path(tmp), enabled=True, verbosity="events")
            console.start_run()
            console.event("pressed F")
            console.result("scroll ok")
            console.process("drag step")
            path = console.flush()
            assert path is not None
            text = path.read_text(encoding="utf-8")
            self.assertIn("pressed F", text)
            self.assertNotIn("scroll ok", text)
            self.assertNotIn("drag step", text)

    def test_user_comment_always_logged_with_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            console = ConsoleSession(project_root=Path(tmp), enabled=True, verbosity="events")
            console.start_run()
            self.assertTrue(console.user_comment("looks wrong on slot 3"))
            path = console.flush()
            assert path is not None
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, r"\d{2}:\d{2}:\d{2} \[comment\] User Comment: looks wrong on slot 3")

    def test_display_can_hide_timestamps_but_dump_keeps_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            console = ConsoleSession(project_root=Path(tmp), enabled=True, verbosity="results")
            console.start_run()
            console.event("pressed 1")
            shown = console.snapshot(show_timestamps=False)
            self.assertTrue(any(line.startswith("[events]") for line in shown))
            self.assertFalse(any(line[:2].isdigit() and line[2] == ":" for line in shown))
            dump = console.dump_text()
            self.assertRegex(dump, r"\d{2}:\d{2}:\d{2} \[events\]")


class ConsoleSettingsPersistTests(unittest.TestCase):
    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            settings = Settings(
                lco_console_enabled=True,
                lco_console_verbosity="process",
                lco_console_geometry="560x420+40+80",
            )
            save_settings(path, settings)
            loaded, err = load_settings(path)
            self.assertIsNone(err)
            self.assertTrue(loaded.lco_console_enabled)
            self.assertEqual(loaded.lco_console_verbosity, "process")
            self.assertEqual(loaded.lco_console_geometry, "560x420+40+80")


class ConsoleHotkeyTests(unittest.TestCase):
    def test_console_hotkeys_removed_from_lco(self) -> None:
        pb = load_playbook(default_playbook_path(project_root()))
        self.assertIsNone(pb.action_for_token("Y"))
        self.assertIsNone(pb.action_for_token("H"))


if __name__ == "__main__":
    unittest.main()
