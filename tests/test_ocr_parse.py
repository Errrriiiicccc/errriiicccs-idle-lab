import unittest

from idle_lab.automations.ocr import (
    parse_currency,
    parse_game_over,
    parse_presence,
    parse_signal,
    parse_wave,
)


class OcrParseTests(unittest.TestCase):
    def test_parse_wave(self) -> None:
        self.assertEqual(parse_wave("WAVE 42"), "42")
        self.assertEqual(parse_wave("wave: 7"), "7")
        self.assertEqual(parse_wave("Vave 851"), "851")
        self.assertEqual(parse_wave("1 Wave 851 155."), "851")
        self.assertEqual(parse_wave("nope"), "")

    def test_parse_signal(self) -> None:
        self.assertEqual(parse_signal("SIGNAL A"), "A")
        self.assertEqual(parse_signal("signal b"), "B")

    def test_parse_currency(self) -> None:
        self.assertEqual(parse_currency("12.5B"), "12.5B")
        self.assertEqual(parse_currency("coins 1.2e9"), "1.2e9")
        self.assertEqual(parse_currency("850.2M cash"), "850.2M")
        self.assertEqual(parse_currency("$ 34.77K"), "34.77K")
        self.assertEqual(parse_currency("5) 566.99K"), "566.99K")
        self.assertEqual(parse_currency("$ 294K/min"), "294K")
        self.assertEqual(parse_currency("5 76K / tin"), "5.76K")
        self.assertEqual(parse_currency("nope"), "")

    def test_parse_game_over(self) -> None:
        self.assertEqual(parse_game_over("GAME OVER"), "GAME_OVER")
        self.assertEqual(parse_game_over("You Died — Retry"), "GAME_OVER")
        self.assertEqual(parse_game_over("Wave 612"), "RUNNING")

    def test_parse_presence(self) -> None:
        self.assertEqual(parse_presence("GEM"), "PRESENT")
        self.assertEqual(parse_presence("  "), "ABSENT")
        self.assertEqual(parse_presence("."), "ABSENT")


if __name__ == "__main__":
    unittest.main()
