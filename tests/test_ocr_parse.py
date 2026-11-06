import unittest

from idle_lab.automations.ocr import (
    parse_currency,
    parse_currency_balance,
    parse_currency_int,
    parse_currency_rate,
    parse_game_over,
    parse_presence,
    parse_signal,
    parse_wave,
    sanitize_rate_unit_noise,
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

    def test_sanitize_rate_unit_noise(self) -> None:
        cleaned, saw = sanitize_rate_unit_noise("142/min")
        self.assertTrue(saw)
        self.assertEqual(cleaned, "142")
        cleaned, saw = sanitize_rate_unit_noise("1472m")
        self.assertEqual(cleaned, "1472")
        cleaned, saw = sanitize_rate_unit_noise("$1.24K/min")
        self.assertTrue(saw)
        self.assertIn("1.24K", cleaned)
        self.assertNotIn("min", cleaned.lower())

    def test_parse_currency_legacy(self) -> None:
        self.assertEqual(parse_currency("12.5B"), "12.5B")
        self.assertEqual(parse_currency("coins 1.2e9"), "1.2e9")
        self.assertEqual(parse_currency("850.2M cash"), "850.2M")
        self.assertEqual(parse_currency("$ 34.77K"), "34.77K")
        self.assertEqual(parse_currency("5) 566.99K"), "566.99K")
        self.assertEqual(parse_currency("5 76K / tin"), "5.76K")
        self.assertEqual(parse_currency("11.278K"), "11.28K")
        self.assertEqual(parse_currency("977K"), "9.77K")
        self.assertEqual(parse_currency("1128K"), "11.28K")
        self.assertEqual(parse_currency("488"), "488")
        self.assertEqual(parse_currency("nope"), "")

    def test_parse_currency_balance(self) -> None:
        self.assertEqual(parse_currency_balance("11.28K"), "11.28K")
        self.assertEqual(parse_currency_balance("977K"), "9.77K")
        self.assertEqual(parse_currency_balance("$ 8.61K"), "8.61K")
        self.assertEqual(parse_currency_balance("431"), "431")
        self.assertEqual(parse_currency_balance("1.70K"), "1.7K")
        self.assertEqual(parse_currency_balance("208.6K"), "208.6K")
        # OCR monsters — abstain rather than invent a 6-digit K balance.
        self.assertEqual(parse_currency_balance("270860K"), "")
        self.assertEqual(parse_currency_balance("70860K"), "")

    def test_parse_currency_rate(self) -> None:
        self.assertEqual(parse_currency_rate("$ 294K/min"), "294K")
        self.assertEqual(parse_currency_rate(".168K/min"), "1.68K")
        self.assertEqual(parse_currency_rate("168K/min"), "1.68K")
        self.assertEqual(parse_currency_rate("148K/min"), "1.48K")
        self.assertEqual(parse_currency_rate("11 68K/min"), "1.68K")
        self.assertEqual(parse_currency_rate("1 68K/min"), "1.68K")
        self.assertEqual(parse_currency_rate("$4.3K/min"), "4.3K")
        self.assertEqual(parse_currency_rate("$3.61K/min"), "3.61K")
        # Plain early-game rates (no K) — must not become millions.
        self.assertEqual(parse_currency_rate("142/min"), "142")
        self.assertEqual(parse_currency_rate("192/min"), "192")
        self.assertEqual(parse_currency_rate("192M"), "192")
        self.assertEqual(parse_currency_rate("©)148K/min"), "1.48K")
        # Four-digit+K often means a missing decimal on rate rows.
        self.assertEqual(parse_currency_rate("2390K/min"), "2.39K")
        self.assertEqual(parse_currency_rate("2390KM"), "2.39K")
        self.assertEqual(parse_currency_rate(".2.30KM"), "2.3K")
        # The catastrophic failure class: OCR invents digits + m from /min.
        self.assertEqual(parse_currency_rate("1472m"), "")
        self.assertEqual(parse_currency_rate("14.72m"), "")
        self.assertEqual(parse_currency_rate("2192m"), "")
        self.assertEqual(parse_currency_rate("21.42m"), "")

    def test_parse_currency_int(self) -> None:
        self.assertEqual(parse_currency_int("488"), "488")
        self.assertEqual(parse_currency_int("m546"), "546")
        self.assertEqual(parse_currency_int("546"), "546")
        self.assertEqual(parse_currency_int("5456"), "5456")
        # Magnitude belongs on balance/rate fields — abstain.
        self.assertEqual(parse_currency_int("12.5K"), "")
        self.assertEqual(parse_currency_int("11.28K"), "")

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
