"""Tray icon helpers (no live notification-area required)."""

from __future__ import annotations

import unittest

from idle_lab.tray import make_tray_image


class TrayImageTests(unittest.TestCase):
    def test_make_tray_image_rgba(self) -> None:
        img = make_tray_image()
        self.assertEqual(img.size, (64, 64))
        self.assertEqual(img.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
