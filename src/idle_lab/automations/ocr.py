"""OCR helpers — observations (raw) and inferences (parsed)."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


class OcrError(RuntimeError):
    """OCR engine failure."""


@dataclass(frozen=True)
class OcrResult:
    observation: str
    inference: str
    meta: dict[str, Any]


_WAVE_RE = re.compile(r"(?:wave\s*)?(\d{1,6})", re.IGNORECASE)
_SIGNAL_RE = re.compile(r"(?:signal\s*)?([AB])\b", re.IGNORECASE)
_TESSERACT_CONFIGURED = False


def find_tesseract() -> str | None:
    """Return a usable tesseract.exe path, or None."""

    env = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
    if env:
        path = Path(env)
        if path.is_dir():
            path = path / "tesseract.exe"
        if path.is_file():
            return str(path)

    which = shutil.which("tesseract")
    if which:
        return which

    for candidate in (
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def configure_tesseract() -> str:
    """Point pytesseract at the binary. Raises OcrError with install hints if missing."""

    global _TESSERACT_CONFIGURED
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover
        raise OcrError("pytesseract is not installed") from exc

    cmd = find_tesseract()
    if not cmd:
        raise OcrError(
            "Tesseract OCR is not installed (or not on PATH). "
            "Install with: winget install --id UB-Mannheim.TesseractOCR -e "
            "Then restart Idle Lab. Or set TESSERACT_CMD to tesseract.exe."
        )
    pytesseract.pytesseract.tesseract_cmd = cmd
    _TESSERACT_CONFIGURED = True
    return cmd


def _prepare(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    # Upscale small ROIs so Tesseract has a better chance.
    if gray.width < 160 or gray.height < 40:
        gray = gray.resize((gray.width * 3, gray.height * 3))
    return ImageOps.autocontrast(gray)


def run_ocr(image: Image.Image, *, config: str = "--psm 7") -> str:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover
        raise OcrError("pytesseract is not installed") from exc
    if not _TESSERACT_CONFIGURED:
        configure_tesseract()
    prepared = _prepare(image)
    try:
        text = pytesseract.image_to_string(prepared, config=config) or ""
    except Exception as exc:  # noqa: BLE001 - surface engine errors
        name = type(exc).__name__
        if "TesseractNotFound" in name or "not installed" in str(exc).lower():
            raise OcrError(
                "Tesseract OCR binary not found. "
                "Install with: winget install --id UB-Mannheim.TesseractOCR -e "
                "Then restart Idle Lab."
            ) from exc
        raise OcrError(str(exc)) from exc
    return text.strip()


def parse_wave(raw: str) -> str:
    match = _WAVE_RE.search(raw.replace(",", ""))
    return match.group(1) if match else ""


def parse_signal(raw: str) -> str:
    match = _SIGNAL_RE.search(raw)
    if match:
        return match.group(1).upper()
    compact = re.sub(r"\s+", "", raw).upper()
    if "A" in compact and "B" not in compact:
        return "A"
    if "B" in compact and "A" not in compact:
        return "B"
    if compact.endswith("A") or compact == "A":
        return "A"
    if compact.endswith("B") or compact == "B":
        return "B"
    return ""


def ocr_field(image: Image.Image, parse_as: str = "raw") -> OcrResult:
    raw = run_ocr(image)
    if parse_as == "wave":
        inference = parse_wave(raw)
    elif parse_as == "signal":
        inference = parse_signal(raw)
    else:
        inference = raw
    return OcrResult(observation=raw, inference=inference, meta={"parse_as": parse_as})
