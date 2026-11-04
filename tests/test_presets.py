import json
import tempfile
import unittest
from pathlib import Path

from idle_lab.models import Settings
from idle_lab.presets import PresetError, PresetStore, load_preset, project_root
from idle_lab.settings_store import load_settings, save_settings


def sample_payload() -> dict:
    return {
        "name": "gems",
        "version": 1,
        "timing_mode": "one_second",
        "loop": True,
        "loop_count": None,
        "notes": "tap the gem",
        "points": [
            {"nx": 0.25, "ny": 0.75, "delay_ms": 950, "hold_ms": 50, "button": "left", "label": "gem"}
        ],
    }


class PresetTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = PresetStore(Path(folder))
            path = Path(folder) / "gems.json"
            path.write_text(json.dumps(sample_payload()), encoding="utf-8")
            errors = store.load_all()
            self.assertEqual(errors, [])
            preset = store.presets[0]
            self.assertEqual(preset.name, "gems")
            self.assertIsNone(preset.loop_count)
            self.assertEqual(preset.points[0].label, "gem")
            preset.points[0].delay_ms = 100
            store.save(preset)
            reloaded = load_preset(Path(preset.path))
            self.assertEqual(reloaded.points[0].delay_ms, 100)
            self.assertEqual(reloaded.notes, "tap the gem")

    def test_rename_replaces_the_old_file(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = PresetStore(Path(folder))
            path = Path(folder) / "gems.json"
            path.write_text(json.dumps(sample_payload()), encoding="utf-8")
            store.load_all()
            preset = store.presets[0]
            preset.name = "weekend route"
            store.save(preset)
            self.assertFalse(path.exists())
            self.assertTrue(Path(preset.path).name.startswith("weekend-route"))

    def test_invalid_files_are_reported_and_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bad.json").write_text(json.dumps({"name": "x", "timing_mode": "nope", "points": []}), encoding="utf-8")
            (root / "right.json").write_text(
                json.dumps(
                    {
                        "name": "right",
                        "timing_mode": "instantaneous",
                        "points": [{"nx": 0, "ny": 0, "delay_ms": 50, "hold_ms": 50, "button": "right"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / "ok.json").write_text(json.dumps(sample_payload()), encoding="utf-8")
            store = PresetStore(root)
            errors = store.load_all()
            self.assertEqual(len(errors), 2)
            self.assertEqual(len(store.presets), 1)

    def test_rejects_bad_numbers(self) -> None:
        payload = sample_payload()
        payload["points"][0]["delay_ms"] = -1
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PresetError):
                load_preset(path)

    def test_shipped_sample_loads(self) -> None:
        store = PresetStore(project_root() / "presets")
        errors = store.load_all()
        self.assertEqual(errors, [])
        self.assertTrue(any(preset.name == "sample three points" for preset in store.presets))
        self.assertTrue(any(preset.name == "humanize atk def loop" for preset in store.presets))

    def test_project_root_finds_this_repo(self) -> None:
        root = project_root()
        self.assertTrue((root / "pyproject.toml").exists())


class SettingsTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            save_settings(
                path,
                Settings(
                    click_method="background",
                    focus_before_run=False,
                    restore_cursor=True,
                    countdown_seconds=3,
                    humanize_level="light",
                ),
            )
            loaded, error = load_settings(path)
            self.assertIsNone(error)
            self.assertEqual(loaded.click_method, "background")
            self.assertFalse(loaded.focus_before_run)
            self.assertEqual(loaded.countdown_seconds, 3)
            self.assertEqual(loaded.humanize_level, "light")

    def test_corrupt_file_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text("{", encoding="utf-8")
            loaded, error = load_settings(path)
            self.assertIsNotNone(error)
            self.assertEqual(loaded.click_method, "foreground")
            self.assertEqual(loaded.humanize_level, "medium")

    def test_missing_humanize_defaults_to_medium(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(
                '{"click_method":"foreground","focus_before_run":true,'
                '"restore_cursor":true,"countdown_seconds":0}\n',
                encoding="utf-8",
            )
            loaded, error = load_settings(path)
            self.assertIsNone(error)
            self.assertEqual(loaded.humanize_level, "medium")


if __name__ == "__main__":
    unittest.main()
