import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from idle_lab.screen_map.batch import (
    Mode,
    ScreenMapController,
    ScreenMapError,
    add_shot,
    create_batch,
)
from idle_lab.screen_map.manifest import load_manifest
from idle_lab.screen_map.names import sanitize_slug, unique_dir


class SanitizeTests(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(sanitize_slug("Main HUD / Run"), "main-hud-run")

    def test_empty_fallback(self) -> None:
        self.assertEqual(sanitize_slug("   "), "shot")
        self.assertEqual(sanitize_slug("@@@", fallback="batch"), "batch")

    def test_unique_dir(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = unique_dir(root, "tower")
            first.mkdir()
            second = unique_dir(root, "tower")
            self.assertEqual(second.name, "tower-2")


class ManifestTests(unittest.TestCase):
    def test_create_and_append(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = create_batch(root, "Tower Pass 1")
            self.assertTrue((session.folder / "manifest.json").exists())
            image = Image.new("RGB", (8, 8), color=(12, 34, 56))
            shot = add_shot(
                session,
                title="Workshop",
                image=image,
                anchor={"window_title": "BlueStacks", "width": 100, "height": 200},
            )
            self.assertEqual(shot.index, 1)
            self.assertEqual(shot.filename, "01_workshop.png")
            self.assertTrue((session.folder / shot.filename).exists())
            loaded = load_manifest(session.folder)
            self.assertEqual(loaded.batch_title, "Tower Pass 1")
            self.assertEqual(len(loaded.shots), 1)
            self.assertEqual(loaded.shots[0].title, "Workshop")
            self.assertIsNone(loaded.shots[0].classification)
            self.assertIsNone(loaded.shots[0].how_opened)
            self.assertIsNone(loaded.shots[0].notes)
            raw = json.loads((session.folder / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(raw["shots"][0]["anchor"]["width"], 100)

    def test_rejects_empty_titles(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ScreenMapError):
                create_batch(root, "  ")
            session = create_batch(root, "ok")
            image = Image.new("RGB", (4, 4), color=0)
            with self.assertRaises(ScreenMapError):
                add_shot(session, title=" ", image=image, anchor=None)


class ModeMachineTests(unittest.TestCase):
    def test_lifecycle(self) -> None:
        controller = ScreenMapController()
        self.assertEqual(controller.mode, Mode.IDLE)
        with tempfile.TemporaryDirectory() as folder:
            session = create_batch(Path(folder), "mode-test")
            controller.start(session)
            self.assertTrue(controller.active)
            self.assertEqual(controller.mode, Mode.ACTIVE)
            controller.begin_title_dialog()
            self.assertTrue(controller.dialog_open)
            controller.cancel_title_dialog()
            self.assertEqual(controller.mode, Mode.ACTIVE)
            controller.begin_title_dialog()
            controller.finish_title_dialog()
            self.assertEqual(controller.mode, Mode.ACTIVE)
            ended = controller.end()
            self.assertIs(ended, session)
            self.assertFalse(controller.active)

    def test_cannot_title_when_idle(self) -> None:
        controller = ScreenMapController()
        with self.assertRaises(ScreenMapError):
            controller.begin_title_dialog()


if __name__ == "__main__":
    unittest.main()
