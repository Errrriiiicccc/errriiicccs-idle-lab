"""PoC tests for HUD balances-vs-rates discriminator."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image

from idle_lab.automations.hud_mode import detect_hud_currency_mode
from idle_lab.automations.ocr import configure_tesseract

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ocr"


class HudModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configure_tesseract()

    def test_balance_crop_is_balances(self) -> None:
        path = FIXTURE_DIR / "coins_11.28K.png"
        if not path.is_file():
            self.skipTest("fixture missing")
        result = detect_hud_currency_mode(Image.open(path).convert("RGB"))
        self.assertEqual(result.mode, "balances")

    def test_rate_crop_is_rates(self) -> None:
        path = FIXTURE_DIR / "cpm_1.68K.png"
        if not path.is_file():
            self.skipTest("fixture missing")
        result = detect_hud_currency_mode(Image.open(path).convert("RGB"))
        self.assertEqual(result.mode, "rates")

    def test_live_rate_crop_is_rates(self) -> None:
        path = FIXTURE_DIR / "cpm_2.39K.png"
        if not path.is_file():
            self.skipTest("fixture missing")
        result = detect_hud_currency_mode(Image.open(path).convert("RGB"))
        self.assertEqual(result.mode, "rates")


if __name__ == "__main__":
    unittest.main()
