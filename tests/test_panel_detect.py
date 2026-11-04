import unittest
from pathlib import Path

from PIL import Image

from idle_lab.ai_batch.panel_detect import detect_upgrade_panel

SM2 = Path(__file__).resolve().parents[1] / "screen-maps" / "ai-run-menu-nav-currency-toggle-lab-2"
SM1 = Path(__file__).resolve().parents[1] / "screen-maps" / "ai-run-menu-nav-currency-toggle-lab"


@unittest.skipUnless(SM2.exists(), "local screen-map shots not present")
class PanelDetectLiveShotsTests(unittest.TestCase):
    def test_observe_is_attack_open(self) -> None:
        image = Image.open(SM2 / "01_observe-before-scroll-lab.png")
        state = detect_upgrade_panel(image)
        self.assertTrue(state.panel_open)
        self.assertEqual(state.tab, "attack")

    def test_defense_shot(self) -> None:
        image = Image.open(SM2 / "08_defense-scroll-00-before.png")
        state = detect_upgrade_panel(image)
        self.assertTrue(state.panel_open)
        self.assertEqual(state.tab, "defense")

    def test_utility_shot(self) -> None:
        image = Image.open(SM2 / "13_utility-panel-open-confirm.png")
        state = detect_upgrade_panel(image)
        self.assertTrue(state.panel_open)
        self.assertEqual(state.tab, "utility")


@unittest.skipUnless(SM1.exists(), "local screen-map shots not present")
class PanelDetectClosedTests(unittest.TestCase):
    def test_closed_combat_footer(self) -> None:
        image = Image.open(SM1 / "04_attack-scroll-00-top.png")
        state = detect_upgrade_panel(image)
        self.assertFalse(state.panel_open)
        self.assertIsNone(state.tab)


class PanelDetectSyntheticTests(unittest.TestCase):
    def test_dark_is_closed(self) -> None:
        image = Image.new("RGB", (200, 400), color=(10, 10, 15))
        state = detect_upgrade_panel(image)
        self.assertFalse(state.panel_open)


if __name__ == "__main__":
    unittest.main()
