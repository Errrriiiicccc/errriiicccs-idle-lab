import tempfile
import unittest
from pathlib import Path

from PIL import Image

from idle_lab.ai_batch.schema import RequestResult
from idle_lab.ai_batch.store import AiBatchError, AiBatchStore, create_from_ai_spec
from idle_lab.screen_map.batch import add_shot, create_batch
from idle_lab.screen_map.catalog import list_batches
from idle_lab.scroll_memory import ScrollMemory


class AiBatchStoreTests(unittest.TestCase):
    def test_create_reload_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root)
            batch = store.create(
                "Workshop Pass",
                goal="menus",
                created_by="ai",
                requests=[
                    {"id": "r1", "kind": "screenshot", "label": "Workshop"},
                    {"id": "r2", "kind": "note", "label": "Gaps"},
                ],
            )
            self.assertEqual(batch.status, "pending")
            self.assertTrue((batch_folder := store.folder_for(batch.slug)) is not None)
            self.assertTrue((batch_folder / "batch.json").exists())

            store.mark_request(
                batch,
                "r1",
                status="done",
                result=RequestResult(summary="captured", path="shot.png"),
            )
            self.assertEqual(batch.status, "partial")
            store.mark_request(batch, "r2", status="done", result=RequestResult(summary="none"))
            self.assertEqual(batch.status, "completed")
            self.assertIsNotNone(batch.completed_at)

            store.add_feedback(batch, "Missed cards tab", author="human")
            reloaded = AiBatchStore(root)
            errors = reloaded.load_all()
            self.assertEqual(errors, [])
            again = reloaded.batches[batch.slug]
            self.assertEqual(again.status, "completed")
            self.assertEqual(len(again.feedback), 1)
            completed = reloaded.list_batches(status_filter="completed")
            self.assertEqual(len(completed), 1)

    def test_create_from_ai_spec(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            batch = create_from_ai_spec(
                root,
                {
                    "name": "Lab gather",
                    "goal": "lab",
                    "requests": [{"id": "a", "kind": "event_snapshot", "label": "OCR"}],
                },
            )
            self.assertEqual(batch.created_by, "ai")
            self.assertEqual(batch.requests[0].kind, "event_snapshot")

    def test_rejects_empty_name(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            store = AiBatchStore(Path(folder))
            with self.assertRaises(AiBatchError):
                store.create("  ")


class ScreenMapCatalogTests(unittest.TestCase):
    def test_list_batches(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = create_batch(root, "Pass One")
            image = Image.new("RGB", (4, 4), color=1)
            add_shot(session, title="HUD", image=image, anchor=None)
            batches = list_batches(root)
            self.assertEqual(len(batches), 1)
            self.assertEqual(batches[0].title, "Pass One")
            self.assertEqual(batches[0].shot_count, 1)
            self.assertTrue(batches[0].shot_path(batches[0].manifest.shots[0]).exists())


class ScrollMemoryTests(unittest.TestCase):
    def test_remember_restore_dict(self) -> None:
        memory = ScrollMemory()
        memory._tops["demo"] = 0.42
        self.assertEqual(memory._tops["demo"], 0.42)
        memory.remember_prefix("missing.")  # no frames — no crash
        memory.restore_prefix("missing.")


if __name__ == "__main__":
    unittest.main()
