import unittest
from unittest import mock

from idle_lab.automations.ocr import find_tesseract


class TesseractLocateTests(unittest.TestCase):
    def test_finds_program_files_install(self) -> None:
        path = find_tesseract()
        # On Eric's machine after winget install this should resolve; skip if absent in CI.
        if path is None:
            self.skipTest("tesseract not installed on this machine")
        self.assertTrue(path.lower().endswith("tesseract.exe"))

    def test_env_override(self) -> None:
        with mock.patch.dict("os.environ", {"TESSERACT_CMD": r"C:\fake\tesseract.exe"}):
            with mock.patch("idle_lab.automations.ocr.Path.is_file", return_value=True):
                with mock.patch("idle_lab.automations.ocr.Path.is_dir", return_value=False):
                    self.assertEqual(find_tesseract(), r"C:\fake\tesseract.exe")


if __name__ == "__main__":
    unittest.main()
