"""HUD currency-mode discriminator (balances vs /min rates).

Anticipated uses:
- Branch before OCR so we don't parse a balance crop as a rate (or vice versa)
- Confirm currency-toggle preset actually flipped the HUD
- Flight-deck / mission asserts: "expect rates mode before reading coins/min"

This is a cheap text cue — not a template match. Prefer ROI crops of the
coins (or cash) row; presence of `/min` or a trailing `min` → rates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from PIL import Image

from idle_lab.automations.ocr import configure_tesseract, run_ocr, strip_left_icon

HudCurrencyMode = Literal["balances", "rates", "unknown"]

_RATE_CUE_RE = re.compile(r"/\s*min|\bmin\b", re.IGNORECASE)
_BALANCE_SHAPE_RE = re.compile(
    r"\d{1,3}(?:\.\d{1,2})?\s*[KMBT]\b|\b\d{2,6}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HudModeResult:
    mode: HudCurrencyMode
    observation: str
    confidence: float
    meta: dict


def detect_hud_currency_mode(image: Image.Image) -> HudModeResult:
    """Classify a currency-row crop as balances, rates, or unknown.

    Tries a couple of light preps; does not run the full multi-strip currency
    stack — mode detection should stay cheap enough for every tick.
    """

    configure_tesseract()
    observations: list[str] = []
    for strip in (0.0, 0.18):
        work = strip_left_icon(image, strip) if strip > 0 else image
        for threshold in (None, 150):
            raw = run_ocr(
                work,
                config="--psm 7 -c tessedit_char_whitelist=0123456789.$/KMBTminMIN ",
                scale=3,
                threshold=threshold,
            )
            if raw:
                observations.append(raw)

    joined = " | ".join(observations)
    rate_hits = sum(1 for raw in observations if _RATE_CUE_RE.search(raw))
    balance_hits = sum(
        1
        for raw in observations
        if _BALANCE_SHAPE_RE.search(raw) and not _RATE_CUE_RE.search(raw)
    )

    if rate_hits >= 1 and rate_hits >= balance_hits:
        mode: HudCurrencyMode = "rates"
        confidence = min(1.0, 0.55 + 0.15 * rate_hits)
    elif balance_hits >= 1 and rate_hits == 0:
        mode = "balances"
        confidence = min(1.0, 0.55 + 0.15 * balance_hits)
    else:
        mode = "unknown"
        confidence = 0.2

    return HudModeResult(
        mode=mode,
        observation=joined,
        confidence=confidence,
        meta={
            "rate_hits": rate_hits,
            "balance_hits": balance_hits,
            "samples": len(observations),
        },
    )
