import unittest

from PIL import Image

from idle_lab.ai_batch.scroll_metrics import crop_normalized, mean_abs_diff


class MeanAbsDiffTests(unittest.TestCase):
    def test_identical_is_zero(self) -> None:
        image = Image.new("RGB", (20, 20), color=(10, 20, 30))
        self.assertAlmostEqual(mean_abs_diff(image, image.copy()), 0.0)

    def test_full_white_vs_black_is_one(self) -> None:
        black = Image.new("RGB", (8, 8), color=(0, 0, 0))
        white = Image.new("RGB", (8, 8), color=(255, 255, 255))
        self.assertAlmostEqual(mean_abs_diff(black, white), 1.0, places=3)

    def test_small_change_is_below_typical_threshold(self) -> None:
        base = Image.new("RGB", (40, 40), color=(40, 40, 40))
        tweaked = base.copy()
        tweaked.putpixel((0, 0), (41, 40, 40))
        self.assertLess(mean_abs_diff(base, tweaked), 0.012)


class CropNormalizedTests(unittest.TestCase):
    def test_crop_center(self) -> None:
        image = Image.new("RGB", (100, 100), color=(0, 0, 0))
        for x in range(40, 60):
            for y in range(40, 60):
                image.putpixel((x, y), (255, 0, 0))
        crop = crop_normalized(image, nx=0.4, ny=0.4, nw=0.2, nh=0.2)
        self.assertGreaterEqual(crop.width, 15)
        self.assertGreaterEqual(crop.height, 15)
        self.assertEqual(crop.getpixel((crop.width // 2, crop.height // 2)), (255, 0, 0))


if __name__ == "__main__":
    unittest.main()
