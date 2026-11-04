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


_WAVE_LABELED_RE = re.compile(r"(?:wave|vave)\s*[^\d]{0,3}(\d{1,6})", re.IGNORECASE)
_WAVE_RE = re.compile(r"(?:wave\s*)?(\d{1,6})", re.IGNORECASE)
_SIGNAL_RE = re.compile(r"(?:signal\s*)?([AB])\b", re.IGNORECASE)
# Tower-style numbers: 1.2e9, 12.5B, 850.2M, 1,234,567, plain ints.
_CURRENCY_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*([eE][+\-]?\d+|[KMBTQkmbtq])?",
)
_GAME_OVER_RE = re.compile(
    r"(game\s*over|you\s*(died|lose|lost)|defeat|run\s*ended|try\s*again|retry)",
    re.IGNORECASE,
)
_PRESENCE_NOISE_RE = re.compile(r"^[\s|_.:;,\-]+$")
_TESSERACT_CONFIGURED = False

_CURRENCY_WHITELIST = "0123456789.$/KMBTkmbtEe+-minMIN "
_WAVE_WHITELIST = "WaveVavWAVE 0123456789"


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


def _prepare(image: Image.Image, *, invert: bool = False, scale: int = 3) -> Image.Image:
    gray = ImageOps.grayscale(image)
    scale = max(1, int(scale))
    gray = gray.resize((max(1, gray.width * scale), max(1, gray.height * scale)))
    gray = ImageOps.autocontrast(gray)
    if invert:
        gray = ImageOps.invert(gray)
    return gray


def run_ocr(
    image: Image.Image,
    *,
    config: str = "--psm 7",
    invert: bool = False,
    scale: int = 3,
) -> str:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover
        raise OcrError("pytesseract is not installed") from exc
    if not _TESSERACT_CONFIGURED:
        configure_tesseract()
    prepared = _prepare(image, invert=invert, scale=scale)
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
    """Prefer the number after Wave/Vave so nearby HUD digits do not win."""

    text = raw.replace(",", " ")
    labeled = _WAVE_LABELED_RE.search(text)
    if labeled:
        return labeled.group(1)
    match = _WAVE_RE.search(text)
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


def parse_currency(raw: str) -> str:
    """Return the best Tower-ish quantity token, preserving suffix (e.g. 12.5B, 1.2e9)."""

    text = raw.replace(",", "")
    # Common OCR confusion on coin rows: S66 → treat S as 5 when stuck to digits.
    text = re.sub(r"(?<=\D)[Ss](?=\d)", "5", text)
    text = re.sub(r"(?<=\s)[Ss](?=\d)", "5", text)
    # Recover split decimals: "5 76K" / "566 99K" → "5.76K" / "566.99K"
    text = re.sub(r"(\d)\s+(\d{2})\s*([KMBT])\b", r"\1.\2\3", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)\s*\.\s*(\d{2})\s*([KMBT])\b", r"\1.\2\3", text, flags=re.IGNORECASE)

    scored: list[tuple[int, str]] = []
    for match in _CURRENCY_RE.finditer(text):
        number, suffix = match.group(1), match.group(2) or ""
        number = number.replace(",", ".")
        token = f"{number}{suffix}"
        score = len(re.sub(r"\D", "", number))
        if suffix:
            score += 10
        if "." in number:
            score += 5
        # Tiny leading junk like "5)" before "566.99K" should lose.
        if len(re.sub(r"\D", "", number)) <= 1 and not suffix:
            score -= 5
        scored.append((score, token))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def parse_game_over(raw: str) -> str:
    """Infer GAME_OVER vs RUNNING from center-dialog OCR."""

    if _GAME_OVER_RE.search(raw or ""):
        return "GAME_OVER"
    return "RUNNING"


def parse_presence(raw: str) -> str:
    """PRESENT if OCR saw non-trivial text in the ROI, else ABSENT."""

    text = (raw or "").strip()
    if not text or _PRESENCE_NOISE_RE.match(text):
        return "ABSENT"
    # Ignore tiny OCR noise (1–2 junk glyphs).
    alnum = re.sub(r"[^A-Za-z0-9]", "", text)
    if len(alnum) < 2:
        return "ABSENT"
    return "PRESENT"


def _infer(parse_as: str, raw: str) -> str:
    if parse_as == "wave":
        return parse_wave(raw)
    if parse_as == "signal":
        return parse_signal(raw)
    if parse_as == "currency":
        return parse_currency(raw)
    if parse_as == "game_over":
        return parse_game_over(raw)
    if parse_as == "presence":
        return parse_presence(raw)
    return raw


def ocr_field(image: Image.Image, parse_as: str = "raw") -> OcrResult:
    """OCR a crop. For wave/currency, try a couple of prep modes and keep the best parse."""

    attempts: list[tuple[str, bool, str]] = []
    if parse_as == "wave":
        attempts = [
            (f"--psm 7 -c tessedit_char_whitelist={_WAVE_WHITELIST}", False, "--psm 7"),
            (f"--psm 7 -c tessedit_char_whitelist={_WAVE_WHITELIST}", True, "--psm 7 invert"),
            ("--psm 7", False, "--psm 7 plain"),
            ("--psm 7", True, "--psm 7 invert"),
        ]
    elif parse_as == "currency":
        attempts = [
            (f"--psm 7 -c tessedit_char_whitelist={_CURRENCY_WHITELIST}", False, "currency wl"),
            ("--psm 7", False, "plain"),
            ("--psm 7", True, "invert"),
        ]
    else:
        attempts = [("--psm 7", False, "default")]

    best_raw = ""
    best_inference = ""
    best_score = -10_000
    best_meta: dict[str, Any] = {"parse_as": parse_as}

    def _score(parse_as_local: str, raw: str, inference: str) -> int:
        if not inference:
            return -1
        if parse_as_local == "wave":
            return 100 if _WAVE_LABELED_RE.search(raw or "") else 10
        if parse_as_local == "currency":
            score = len(re.sub(r"\D", "", inference))
            if re.search(r"[KMBT]$", inference, re.I):
                score += 10
            if "." in inference:
                score += 20  # keep 5.76K over 576K
            if re.search(r"/\s*min", raw or "", re.I):
                score += 5
            return score
        return 1

    for config, invert, label in attempts:
        raw = run_ocr(image, config=config, invert=invert)
        inference = _infer(parse_as, raw)
        score = _score(parse_as, raw, inference)
        if score > best_score:
            best_score = score
            best_raw = raw
            best_inference = inference
            best_meta["prep"] = label
        if parse_as == "wave" and _WAVE_LABELED_RE.search(raw or "") and inference:
            break

    if parse_as not in {"wave", "currency"}:
        best_raw = run_ocr(image)
        best_inference = _infer(parse_as, best_raw)
        best_meta = {"parse_as": parse_as}

    return OcrResult(observation=best_raw, inference=best_inference, meta=best_meta)
