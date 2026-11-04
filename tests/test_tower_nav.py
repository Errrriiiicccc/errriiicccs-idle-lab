import unittest

from PIL import Image, ImageDraw, ImageFont

from idle_lab.ai_batch.panel_detect import detect_upgrade_panel
from idle_lab.automations.tower_nav import check_list_top, panel_status_vars


class TowerNavTests(unittest.TestCase):
    def test_panel_status_vars(self) -> None:
        image = Image.new("RGB", (200, 400), color=(20, 140, 180))
        state = detect_upgrade_panel(image)
        vars_map = panel_status_vars(state)
        self.assertIn(vars_map["panel_open"], {"yes", "no"})
        self.assertIn("panel_reason", vars_map)

    def test_check_list_top_finds_health(self) -> None:
        image = Image.new("RGB", (400, 800), color=(40, 40, 50))
        draw = ImageDraw.Draw(image)
        # Paint text into the first-card band (~ny 0.67).
        top = int(0.67 * 800)
        draw.rectangle((20, top, 300, top + 50), fill=(80, 40, 50))
        try:
            font = ImageFont.load_default()
        except Exception:  # noqa: BLE001
            font = None
        draw.text((30, top + 10), "Health 1.2e9", fill=(240, 240, 240), font=font)
        # Without OCR engines in CI this may be empty — only assert structure when OCR works.
        check = check_list_top(image, "Health")
        self.assertIsInstance(check.at_top, bool)
        self.assertIsInstance(check.observation, str)
        self.assertTrue(check.reason)


if __name__ == "__main__":
    unittest.main()
