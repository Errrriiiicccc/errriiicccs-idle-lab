"""Buy-grid edge detection for Live Control snap / live slots."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from idle_lab.live_control.buy_detect import _dedupe_spaced, detect_buy_grid
from idle_lab.presets import project_root


class BuyDetectTests(unittest.TestCase):
    def test_dedupe_spaced_drops_mid_card_edges(self) -> None:
        # Tops at full-card pitch plus a fake mid-card line between 1 and 2.
        tops = [0.70, 0.73, 0.79, 0.88]
        kept = _dedupe_spaced(tops, min_gap=0.070)
        self.assertEqual(kept, [0.70, 0.79, 0.88])

    def test_synthetic_rows_keep_distinct_slot_nys(self) -> None:
        # 593×1028-ish canvas with three card rows in the list band.
        image = Image.new("RGB", (593, 1028), (20, 24, 30))
        draw = ImageDraw.Draw(image)
        list_top = int(0.58 * 1028)
        # Header + three card tops spaced like buy_grid.row_dy≈0.088.
        for ny in (0.62, 0.70, 0.788, 0.876):
            y = int(ny * 1028)
            draw.line((20, y, 560, y), fill=(220, 220, 230), width=3)
            # Extra mid-card noise that used to create duplicate 1/3 parking.
            if ny > 0.62:
                draw.line((40, y + 18, 540, y + 18), fill=(90, 100, 110), width=1)
        detection = detect_buy_grid(image)
        self.assertGreaterEqual(len(detection.row_nys), 2, msg=detection.reason)
        for earlier, later in zip(detection.row_nys, detection.row_nys[1:]):
            self.assertGreaterEqual(later - earlier, 0.065, msg=detection.row_nys)
        # Left column slots (1,3,5) must not share a ny.
        left = [s.ny for s in detection.slots if s.index % 2 == 1]
        self.assertEqual(len(left), len(set(round(v, 3) for v in left)))

    def test_attack_top_is_snapped(self) -> None:
        path = (
            project_root()
            / "screen-maps"
            / "ai-run-upgrade-scroll-controlled"
            / "06_attack-10-status-top.png"
        )
        if not path.is_file():
            self.skipTest(f"missing calibration shot {path}")
        detection = detect_buy_grid(Image.open(path))
        self.assertTrue(detection.snapped, msg=detection.reason)
        self.assertGreaterEqual(len(detection.slots), 4)
        # Row centers should sit in the upgrade list band.
        for slot in detection.slots:
            self.assertGreater(slot.ny, 0.65)
            self.assertLess(slot.ny, 0.93)
            self.assertIn(round(slot.nx, 2), {0.32, 0.72})

    def test_session_start_attack_snapped(self) -> None:
        path = project_root() / "screen-maps" / "observation-2026-11-06-1526" / "01_session-start.png"
        if not path.is_file():
            self.skipTest(f"missing observation shot {path}")
        detection = detect_buy_grid(Image.open(path))
        self.assertTrue(detection.snapped, msg=detection.reason)
        self.assertGreaterEqual(len(detection.slots), 4)


if __name__ == "__main__":
    unittest.main()
