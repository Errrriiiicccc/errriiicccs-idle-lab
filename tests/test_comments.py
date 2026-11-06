import tempfile
import unittest
from pathlib import Path

from idle_lab.comments import CommentStore, mission_comment_path, screen_map_shot_comment_path


class CommentStoreTests(unittest.TestCase):
    def test_round_trip_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "lab-comments.json"
            store = CommentStore(path)
            key = mission_comment_path("demo")
            store.set(key, "  scroll was short  ")
            self.assertTrue(store.has(key))
            self.assertEqual(store.get(key), "scroll was short")

            again = CommentStore(path)
            again.load()
            self.assertEqual(again.get(key), "scroll was short")

            again.set(key, "   ")
            self.assertFalse(again.has(key))
            empty = CommentStore(path)
            self.assertEqual(empty.load(), [])
            self.assertEqual(empty.get(key), "")

    def test_shot_path_keys_differ_from_batch(self) -> None:
        batch = "screen-maps/ai-run-x"
        shot = screen_map_shot_comment_path("ai-run-x", "01.png")
        self.assertNotEqual(batch, shot)
        self.assertIn("shots/01.png", shot)


if __name__ == "__main__":
    unittest.main()
