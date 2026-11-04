import csv
import tempfile
import unittest
from pathlib import Path

from idle_lab.automations.csv_log import CSV_FIELDS, append_run_row


class CsvLogTests(unittest.TestCase):
    def test_append_creates_header_and_row(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run_log.csv"
            row = append_run_row(path, run_number=1, wave_number=42, when="2026-11-04T20:15:00-05:00")
            self.assertEqual(row["wave_number"], "42")
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0].keys()), list(CSV_FIELDS))
            self.assertEqual(rows[0]["run_number"], "1")
            self.assertEqual(rows[0]["wave_number"], "42")

    def test_second_append_keeps_one_header(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run_log.csv"
            append_run_row(path, run_number=1, wave_number=1, when="t1")
            append_run_row(path, run_number=1, wave_number=2, when="t2")
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
