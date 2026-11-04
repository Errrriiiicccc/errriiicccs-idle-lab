import unittest

from idle_lab.automations.ocr import parse_signal, parse_wave


class OcrParseTests(unittest.TestCase):
    def test_parse_wave(self) -> None:
        self.assertEqual(parse_wave("WAVE 42"), "42")
        self.assertEqual(parse_wave("wave: 7"), "7")
        self.assertEqual(parse_wave("nope"), "")

    def test_parse_signal(self) -> None:
        self.assertEqual(parse_signal("SIGNAL A"), "A")
        self.assertEqual(parse_signal("signal b"), "B")


if __name__ == "__main__":
    unittest.main()
