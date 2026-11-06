import tempfile
import unittest
from pathlib import Path
from PIL import Image

from idle_lab.ai_batch.runner import AiBatchRunner, AiBatchRunnerError
from idle_lab.ai_batch.schema import BatchRequest
from idle_lab.ai_batch.store import AiBatchStore
from idle_lab.models import Rect


class SchemaStepsTests(unittest.TestCase):
    def test_steps_round_trip(self) -> None:
        req = BatchRequest.from_dict(
            {
                "id": "r1",
                "kind": "screenshot",
                "label": "Shot",
                "steps": [{"action": "screenshot", "title": "a"}],
            }
        )
        self.assertTrue(req.runnable)
        self.assertEqual(req.to_dict()["steps"][0]["action"], "screenshot")


class RunnerGuardTests(unittest.TestCase):
    def test_refuses_without_steps(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai")
            batch = store.create("Empty steps", requests=[{"id": "a", "kind": "note", "label": "n"}])
            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("missing", None, None, None),
            )
            with self.assertRaises(AiBatchRunnerError):
                runner.start(batch)


class RunnerHappyPathTests(unittest.TestCase):
    def test_screenshot_step_writes_screen_map(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai")
            batch = store.create(
                "Shot only",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "screenshot",
                        "label": "One",
                        "steps": [{"action": "screenshot", "title": "hello"}],
                    }
                ],
            )
            rect = Rect(0, 0, 20, 20)

            def fake_grab(_rect):
                return Image.new("RGB", (8, 8), color=(1, 2, 3))

            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("ok", 1, rect, "Win"),
            )
            import idle_lab.ai_batch.runner as runner_mod

            original = runner_mod.grab_anchor
            runner_mod.grab_anchor = fake_grab  # type: ignore[assignment]
            try:
                runner.start(batch)
                runner._thread.join(timeout=5)  # noqa: SLF001
            finally:
                runner_mod.grab_anchor = original  # type: ignore[assignment]

            store.load_all()
            again = store.batches[batch.slug]
            self.assertEqual(again.requests[0].status, "done")
            self.assertTrue(again.linked_screen_map_batches)
            sm = root / "sm" / again.linked_screen_map_batches[0]
            self.assertTrue(sm.exists())
            pngs = list(sm.glob("*.png"))
            self.assertEqual(len(pngs), 1)
            report = store.folder_for(batch.slug)
            self.assertIsNotNone(report)
            self.assertTrue((report / "run_report.json").exists())

    def test_scroll_map_stops_when_roi_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai")
            batch = store.create(
                "Scroll map",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "screen_map_batch",
                        "label": "Map",
                        "steps": [
                            {
                                "action": "scroll_map",
                                "nx": 0.5,
                                "ny": 0.5,
                                "amount": 1,
                                "max_steps": 5,
                                "settle_ms": 0,
                                "settle_confirm_ms": 0,
                                "method": "wheel",
                                "title_prefix": "lab-scroll",
                                "unchanged_threshold": 0.01,
                                "roi": {"nx": 0.0, "ny": 0.0, "nw": 1.0, "nh": 1.0},
                            }
                        ],
                    }
                ],
            )
            rect = Rect(0, 0, 40, 40)
            frames = [
                Image.new("RGB", (20, 20), color=(10, 10, 10)),
                Image.new("RGB", (20, 20), color=(200, 10, 10)),
                Image.new("RGB", (20, 20), color=(200, 10, 10)),
            ]
            call_count = {"n": 0}

            def fake_grab(_rect):
                index = min(call_count["n"], len(frames) - 1)
                call_count["n"] += 1
                return frames[index].copy()

            scroll_calls = {"n": 0}

            def fake_scroll(self, nx, ny, direction, amount, **kwargs):  # noqa: ANN001
                scroll_calls["n"] += 1

            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("ok", 1, rect, "Win"),
            )
            import idle_lab.ai_batch.runner as runner_mod

            original_grab = runner_mod.grab_anchor
            original_scroll = AiBatchRunner._scroll
            runner_mod.grab_anchor = fake_grab  # type: ignore[assignment]
            AiBatchRunner._scroll = fake_scroll  # type: ignore[method-assign]
            try:
                runner.start(batch)
                runner._thread.join(timeout=5)  # noqa: SLF001
            finally:
                runner_mod.grab_anchor = original_grab  # type: ignore[assignment]
                AiBatchRunner._scroll = original_scroll  # type: ignore[method-assign]

            store.load_all()
            again = store.batches[batch.slug]
            self.assertEqual(again.requests[0].status, "done")
            payload = again.requests[0].result.payload if again.requests[0].result else None
            self.assertIsNotNone(payload)
            assert payload is not None
            maps = payload.get("scroll_maps") or []
            self.assertEqual(len(maps), 1)
            self.assertTrue(maps[0]["at_bottom"])
            self.assertEqual(maps[0]["stop_reason"], "unchanged")
            self.assertEqual(maps[0]["scrolls_applied"], 2)
            self.assertEqual(scroll_calls["n"], 2)
            self.assertLess(scroll_calls["n"], 5)

    def test_ensure_upgrade_tab_skips_when_already_open(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai")
            batch = store.create(
                "Ensure skip",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "screen_map_shot",
                        "label": "Ensure",
                        "steps": [
                            {
                                "action": "ensure_upgrade_tab",
                                "tab": "attack",
                                "nx": 0.2,
                                "ny": 0.955,
                                "title_prefix": "atk",
                            }
                        ],
                    }
                ],
            )
            rect = Rect(0, 0, 200, 400)
            # Cyan tile body in panel ROI → detect as Attack open.
            attack = Image.new("RGB", (200, 400), color=(10, 10, 10))
            for x in range(16, 184):
                for y in range(232, 304):
                    attack.putpixel((x, y), (50, 120, 155))

            clicks = {"n": 0}

            def fake_click(self, nx, ny, hold_ms):  # noqa: ANN001
                clicks["n"] += 1

            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("ok", 1, rect, "Win"),
            )
            import idle_lab.ai_batch.runner as runner_mod

            original_grab = runner_mod.grab_anchor
            original_click = AiBatchRunner._click
            runner_mod.grab_anchor = lambda _rect: attack.copy()  # type: ignore[assignment]
            AiBatchRunner._click = fake_click  # type: ignore[method-assign]
            try:
                runner.start(batch)
                runner._thread.join(timeout=5)  # noqa: SLF001
            finally:
                runner_mod.grab_anchor = original_grab  # type: ignore[assignment]
                AiBatchRunner._click = original_click  # type: ignore[method-assign]

            store.load_all()
            again = store.batches[batch.slug]
            self.assertEqual(again.requests[0].status, "done")
            payload = again.requests[0].result.payload if again.requests[0].result else None
            assert payload is not None
            ensures = payload.get("ensures") or []
            self.assertEqual(len(ensures), 1)
            self.assertFalse(ensures[0]["clicked"])
            self.assertEqual(clicks["n"], 0)

    def test_scroll_map_seek_top_then_down(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai")
            batch = store.create(
                "Seek top map",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "screen_map_batch",
                        "label": "Map",
                        "steps": [
                            {
                                "action": "scroll_map",
                                "seek_top_first": True,
                                "amount": 1,
                                "max_steps": 5,
                                "max_seek_steps": 5,
                                "settle_ms": 0,
                                "settle_confirm_ms": 0,
                                "method": "wheel",
                                "title_prefix": "lab",
                                "unchanged_threshold": 0.01,
                                "roi": {"nx": 0.0, "ny": 0.0, "nw": 1.0, "nh": 1.0},
                            }
                        ],
                    }
                ],
            )
            rect = Rect(0, 0, 40, 40)
            # before → up moves → up unchanged(top) → top reshoot → down moves → down unchanged
            frames = [
                Image.new("RGB", (20, 20), color=(30, 30, 30)),  # before
                Image.new("RGB", (20, 20), color=(80, 30, 30)),  # after seek-up 1
                Image.new("RGB", (20, 20), color=(80, 30, 30)),  # seek-up unchanged
                Image.new("RGB", (20, 20), color=(80, 30, 30)),  # top reshoot
                Image.new("RGB", (20, 20), color=(30, 80, 30)),  # down 1
                Image.new("RGB", (20, 20), color=(30, 80, 30)),  # down unchanged
            ]
            call_count = {"n": 0}
            directions: list[str] = []

            def fake_grab(_rect):
                index = min(call_count["n"], len(frames) - 1)
                call_count["n"] += 1
                return frames[index].copy()

            def fake_scroll(self, nx, ny, direction, amount, **kwargs):  # noqa: ANN001
                directions.append(direction)

            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("ok", 1, rect, "Win"),
            )
            import idle_lab.ai_batch.runner as runner_mod

            original_grab = runner_mod.grab_anchor
            original_scroll = AiBatchRunner._scroll
            runner_mod.grab_anchor = fake_grab  # type: ignore[assignment]
            AiBatchRunner._scroll = fake_scroll  # type: ignore[method-assign]
            try:
                runner.start(batch)
                runner._thread.join(timeout=5)  # noqa: SLF001
            finally:
                runner_mod.grab_anchor = original_grab  # type: ignore[assignment]
                AiBatchRunner._scroll = original_scroll  # type: ignore[method-assign]

            store.load_all()
            again = store.batches[batch.slug]
            payload = again.requests[0].result.payload if again.requests[0].result else None
            assert payload is not None
            maps = payload["scroll_maps"]
            self.assertTrue(maps[0]["seek_top_first"])
            self.assertEqual(maps[0]["seek_top_scrolls"], 2)
            self.assertEqual(maps[0]["scrolls_applied"], 2)
            self.assertTrue(maps[0]["at_bottom"])
            self.assertEqual(directions, ["up", "up", "down", "down"])

    def test_scroll_map_seek_only_max_steps_zero(self) -> None:
        """max_steps: 0 must not coerce to 12 (seek-only prepare steps)."""

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai")
            batch = store.create(
                "Seek only",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "screen_map_batch",
                        "label": "Seek",
                        "steps": [
                            {
                                "action": "scroll_map",
                                "seek_top_first": True,
                                "amount": 1,
                                "max_steps": 0,
                                "max_seek_steps": 5,
                                "settle_ms": 0,
                                "settle_confirm_ms": 0,
                                "method": "wheel",
                                "title_prefix": "lab",
                                "unchanged_threshold": 0.01,
                                "roi": {"nx": 0.0, "ny": 0.0, "nw": 1.0, "nh": 1.0},
                            }
                        ],
                    }
                ],
            )
            rect = Rect(0, 0, 40, 40)
            frames = [
                Image.new("RGB", (20, 20), color=(30, 30, 30)),
                Image.new("RGB", (20, 20), color=(80, 30, 30)),
                Image.new("RGB", (20, 20), color=(80, 30, 30)),
                Image.new("RGB", (20, 20), color=(80, 30, 30)),
            ]
            call_count = {"n": 0}
            directions: list[str] = []

            def fake_grab(_rect):
                index = min(call_count["n"], len(frames) - 1)
                call_count["n"] += 1
                return frames[index].copy()

            def fake_scroll(self, nx, ny, direction, amount, **kwargs):  # noqa: ANN001
                directions.append(direction)

            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("ok", 1, rect, "Win"),
            )
            import idle_lab.ai_batch.runner as runner_mod

            original_grab = runner_mod.grab_anchor
            original_scroll = AiBatchRunner._scroll
            runner_mod.grab_anchor = fake_grab  # type: ignore[assignment]
            AiBatchRunner._scroll = fake_scroll  # type: ignore[method-assign]
            try:
                runner.start(batch)
                runner._thread.join(timeout=5)  # noqa: SLF001
            finally:
                runner_mod.grab_anchor = original_grab  # type: ignore[assignment]
                AiBatchRunner._scroll = original_scroll  # type: ignore[method-assign]

            store.load_all()
            again = store.batches[batch.slug]
            payload = again.requests[0].result.payload if again.requests[0].result else None
            assert payload is not None
            maps = payload["scroll_maps"]
            self.assertEqual(maps[0]["max_steps"], 0)
            self.assertEqual(maps[0]["scrolls_applied"], 0)
            self.assertEqual(maps[0]["seek_top_scrolls"], 2)
            self.assertEqual(directions, ["up", "up"])
            self.assertFalse(any(d == "down" for d in directions))


class OcrFixtureBenchStepTests(unittest.TestCase):
    def test_offline_ocr_fixture_bench_marks_done(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai", examples_root=root / "no-examples")
            batch = store.create(
                "OCR bench",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "other",
                        "label": "Fixtures",
                        "steps": [
                            {
                                "action": "ocr_fixture_bench",
                                "fixture_dir": "tests/fixtures/ocr",
                            }
                        ],
                    }
                ],
            )
            # Persist offline + auto_rerun flags like the seeded example.
            batch.offline = True
            batch.auto_rerun = True
            store.save(batch)

            runner = AiBatchRunner(
                store=store,
                screen_maps_root=root / "sm",
                get_anchor=lambda: ("missing", None, None, None),
            )
            runner.start(batch)
            runner._thread.join(timeout=120)  # noqa: SLF001

            store.load_all()
            again = store.batches[batch.slug]
            self.assertEqual(again.requests[0].status, "done")
            payload = again.requests[0].result.payload if again.requests[0].result else None
            assert payload is not None
            benches = payload.get("ocr_fixture_benches") or []
            self.assertTrue(benches)
            self.assertTrue(benches[0].get("ok"))
            report = store.folder_for(batch.slug)
            assert report is not None
            self.assertTrue((report / "run_report.json").exists())
            self.assertTrue((report / "ocr_fixture_bench.json").exists())

    def test_auto_rerun_requeues_done_requests(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = AiBatchStore(root / "ai", examples_root=root / "no-examples")
            batch = store.create(
                "Rerun me",
                created_by="ai",
                requests=[
                    {
                        "id": "r1",
                        "kind": "other",
                        "label": "Fixtures",
                        "status": "done",
                        "steps": [{"action": "ocr_fixture_bench"}],
                    }
                ],
            )
            batch.auto_rerun = True
            batch.offline = True
            store.save(batch)
            prepared = store.prepare_for_start(store.batches[batch.slug])
            self.assertEqual(prepared.requests[0].status, "pending")


class ExampleSeedTests(unittest.TestCase):
    def test_seeds_ocr_fixture_bench_example(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            examples = root / "examples" / "ai-batches" / "ocr-fixture-bench"
            examples.mkdir(parents=True)
            (examples / "batch.json").write_text(
                '{"name":"OCR fixture bench","slug":"ocr-fixture-bench",'
                '"auto_rerun":true,"offline":true,"requests":[]}\n',
                encoding="utf-8",
            )
            store = AiBatchStore(root / "ai-batches", examples_root=root / "examples" / "ai-batches")
            errors = store.load_all()
            self.assertEqual(errors, [])
            self.assertIn("ocr-fixture-bench", store.batches)
            self.assertEqual(store.last_seeded, ["ocr-fixture-bench"])
            # Second load does not overwrite.
            store.load_all()
            self.assertEqual(store.last_seeded, [])

    def test_seeds_probe_example_with_genre(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            examples = root / "examples" / "ai-batches" / "probe-currency-toggle"
            examples.mkdir(parents=True)
            (examples / "batch.json").write_text(
                '{"name":"Probe: currency","slug":"probe-currency-toggle",'
                '"genre":"probe","auto_rerun":true,"requests":[]}\n',
                encoding="utf-8",
            )
            (examples / "QUESTION.md").write_text("# Question\nDoes it flip?\n", encoding="utf-8")
            store = AiBatchStore(root / "ai-batches", examples_root=root / "examples" / "ai-batches")
            store.load_all()
            batch = store.batches["probe-currency-toggle"]
            self.assertEqual(batch.genre, "probe")
            self.assertTrue((store.folders[batch.slug] / "QUESTION.md").is_file())


class GenreAndProbeScaffoldTests(unittest.TestCase):
    def test_genre_roundtrip(self) -> None:
        from idle_lab.ai_batch.schema import AiBatch, new_batch

        batch = new_batch(name="P", slug="p", genre="probe")
        data = batch.to_dict()
        self.assertEqual(data["genre"], "probe")
        again = AiBatch.from_dict(data)
        self.assertEqual(again.genre, "probe")
        plain = new_batch(name="G", slug="g")
        self.assertNotIn("genre", plain.to_dict())

    def test_probe_iteration_scaffold(self) -> None:
        from idle_lab.ai_batch.iterations import begin_iteration, finalize_iteration

        with tempfile.TemporaryDirectory() as folder:
            batch_dir = Path(folder) / "probe-x"
            batch_dir.mkdir()
            (batch_dir / "batch.json").write_text(
                '{"name":"Probe X","slug":"probe-x","genre":"probe","requests":[]}\n',
                encoding="utf-8",
            )
            iteration = begin_iteration(batch_dir)
            self.assertTrue((batch_dir / "QUESTION.md").is_file())
            self.assertTrue((batch_dir / "ACCEPTANCE.md").is_file())
            self.assertIn("Probe acceptance", (batch_dir / "ACCEPTANCE.md").read_text(encoding="utf-8"))
            finalize_iteration(iteration, run_report={"ok": True})
            reflection = iteration / "reflection.md"
            self.assertTrue(reflection.is_file())
            self.assertIn("Verdict", reflection.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
