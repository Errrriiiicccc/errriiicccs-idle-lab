"""OCR helpers — observations (raw) and inferences (parsed).

Perception model (VISION §§4–5): each parse_as is a typed field contract.
Abstain (empty inference) beats inventing magnitudes. Rate unit noise from
"/min" must never become a million suffix.
"""

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
# Magnitudes: uppercase KMBT + lowercase k/b/t. Never lowercase m ("/min" residue).
_CURRENCY_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*([eE][+\-]?\d+|[KMBTkbt])?",
)
_GAME_OVER_RE = re.compile(
    r"(game\s*over|you\s*(died|lose|lost)|defeat|run\s*ended|try\s*again|retry)",
    re.IGNORECASE,
)
_PRESENCE_NOISE_RE = re.compile(r"^[\s|_.:;,\-]+$")
_TESSERACT_CONFIGURED = False

# Rate whitelist keeps /min readable; magnitude whitelist is uppercase-only so
# OCR "m" from "min" cannot be proposed as a million glyph at the engine layer.
_CURRENCY_WHITELIST = "0123456789.$/KMBTEe+-minMIN "
_DIGITS_SUFFIX_WHITELIST = "0123456789.KMBT "
_RATE_WHITELIST = "0123456789.$/KMBTEe+-minMIN "
_INT_WHITELIST = "0123456789 "
_WAVE_WHITELIST = "WaveVavWAVE 0123456789"

_CURRENCY_FAMILY = frozenset(
    {"currency", "currency_balance", "currency_rate", "currency_int"}
)

# Contracts — inference must match or we abstain.
_BALANCE_CONTRACT = re.compile(
    r"^\d{1,6}(?:\.\d{1,2})?(?:[KMBT]|[eE][+\-]?\d+)?$",
    re.IGNORECASE,
)
_RATE_CONTRACT = re.compile(r"^\d{1,6}(?:\.\d{1,2})?[KMBT]?$", re.IGNORECASE)
_INT_CONTRACT = re.compile(r"^\d{2,4}$")


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


def _prepare(
    image: Image.Image,
    *,
    invert: bool = False,
    scale: int = 3,
    threshold: int | None = None,
) -> Image.Image:
    gray = ImageOps.grayscale(image)
    scale = max(1, int(scale))
    gray = gray.resize((max(1, gray.width * scale), max(1, gray.height * scale)))
    gray = ImageOps.autocontrast(gray)
    if invert:
        gray = ImageOps.invert(gray)
    # Hard threshold clarifies thin strokes (HUD "2" vs "7") that autocontrast alone blurs.
    if threshold is not None:
        cut = max(1, min(254, int(threshold)))
        gray = gray.point(lambda p, c=cut: 255 if p > c else 0)
    return gray


def strip_left_icon(image: Image.Image, fraction: float = 0.28) -> Image.Image:
    """Drop the left portion of a HUD crop (coin/gem/$ icon) so OCR sees digits."""

    fraction = min(0.55, max(0.0, float(fraction)))
    if fraction <= 0 or image.width < 8:
        return image
    left = int(round(image.width * fraction))
    left = min(left, image.width - 4)
    return image.crop((left, 0, image.width, image.height))


def run_ocr(
    image: Image.Image,
    *,
    config: str = "--psm 7",
    invert: bool = False,
    scale: int = 3,
    threshold: int | None = None,
) -> str:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover
        raise OcrError("pytesseract is not installed") from exc
    if not _TESSERACT_CONFIGURED:
        configure_tesseract()
    prepared = _prepare(image, invert=invert, scale=scale, threshold=threshold)
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


def sanitize_rate_unit_noise(raw: str) -> tuple[str, bool]:
    """Strip /min clutter so OCR 'm' cannot become a million suffix.

    Returns (cleaned_text, saw_rate_unit).
    """

    text = (raw or "").replace(",", "")
    saw = bool(re.search(r"/\s*min|\bmin\b", text, flags=re.IGNORECASE))
    text = re.sub(r"/\s*min", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmin\b", " ", text, flags=re.IGNORECASE)
    # Magnitude + glued min residue: 168Km, 2390KM → keep K, drop m/M.
    # Do NOT strip a lone uppercase M magnitude (850.2M cash).
    text = re.sub(r"(?<=[KkBbTt])[mM]\b", "", text)
    # Digit + lowercase m from "/min" without slash: 142m, 1472m.
    if saw or re.search(r"\dm\b", text):
        text = re.sub(r"(?<=\d)m\b", "", text)
        saw = True
    return re.sub(r"\s+", " ", text).strip(), saw


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


def _prep_currency_text(raw: str, *, rate_mode: bool) -> tuple[str, bool]:
    text = (raw or "").replace(",", "")
    text = re.sub(r"(?<=\D)[Ss](?=\d)", "5", text)
    text = re.sub(r"(?<=\s)[Ss](?=\d)", "5", text)
    text, saw_rate = sanitize_rate_unit_noise(text)
    if rate_mode or saw_rate:
        # On rate rows, trailing M after digits is /min residue — not mega.
        text = re.sub(r"(?<=\d)M\b", "", text)
        # Icon-duplicated leading 1 on rate rows.
        text = re.sub(
            r"(?<![\d.])1\s*1\s+(\d{2})\s*([KMBT])\b",
            r"1.\1\2",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"(?<![\d.])1\s+(\d{2})\s*([KMBT])\b",
            r"1.\1\2",
            text,
            flags=re.IGNORECASE,
        )
    # Split decimals: "5 76K" → "5.76K"
    text = re.sub(r"(\d)\s+(\d{2})\s*([KMBT])\b", r"\1.\2\3", text, flags=re.IGNORECASE)
    text = re.sub(r"(\d)\s*\.\s*(\d{2})\s*([KMBT])\b", r"\1.\2\3", text, flags=re.IGNORECASE)

    recovered: list[str] = []
    for match in re.finditer(r"(?<![\d.])\.(\d+)\s*([KMBT])\b", text, flags=re.IGNORECASE):
        digits = match.group(1)
        suffix = match.group(2).upper()
        if len(digits) == 3:
            recovered.append(f"{digits[0]}.{digits[1:]}{suffix}")
        elif len(digits) == 2:
            recovered.append(f"1.{digits}{suffix}")

    if rate_mode or saw_rate:
        # "168K" on a rate row → also try "1.68K" (leading-1 three-digit, K only).
        # Never invent 1.92M from OCR "192M" (/min residue).
        for match in re.finditer(r"(?<![\d.])1(\d{2})\s*([Kk])\b", text):
            recovered.append(f"1.{match.group(1)}K")
        # Four-digit+K without a decimal often means a missing point (2390K → 2.39K).
        for match in re.finditer(r"(?<![\d.])(\d)(\d{2})\d\s*([Kk])\b", text):
            recovered.append(f"{match.group(1)}.{match.group(2)}K")
        # Tesseract sometimes emits ".2.30K" — collapse the leading junk dot.
        text = re.sub(
            r"(?<![\d])\.(\d)\.(\d{1,2})\s*([Kk])\b",
            r"\1.\2K",
            text,
        )
    else:
        # Balance rows: "977K" / "1128K" → "9.77K" / "11.28K".
        for match in re.finditer(
            r"(?<![\d.])(\d{1,2})(\d{2})\s*([KMBT])\b", text, flags=re.IGNORECASE
        ):
            recovered.append(f"{match.group(1)}.{match.group(2)}{match.group(3).upper()}")

    if recovered:
        text = f"{text} {' '.join(recovered)}"
    return text, saw_rate


def _round_hud_number(number: str) -> str:
    if "." not in number:
        return number
    try:
        return f"{round(float(number), 2):.2f}".rstrip("0").rstrip(".")
    except ValueError:
        return number


def _score_currency_token(
    number: str,
    suffix: str,
    *,
    rate_mode: bool,
    saw_rate: bool,
) -> int:
    score = len(re.sub(r"\D", "", number))
    if suffix:
        score += 10
    if "." in number:
        score += 12
    if re.fullmatch(r"\d{1,3}\.\d{1,2}", number) and suffix:
        score += 15
    if len(re.sub(r"\D", "", number)) <= 1 and not suffix:
        score -= 5
    if number.startswith("0."):
        score -= 25
    if rate_mode or saw_rate:
        # Plain 1–3 digit rates are normal early-game; 4+ digit plains are usually OCR junk.
        if not suffix and not "." in number:
            digits = re.sub(r"\D", "", number)
            if len(digits) <= 3:
                score += 8
            else:
                score -= 40
    return score


def _pick_currency_token(text: str, *, rate_mode: bool, saw_rate: bool) -> str:
    scored: list[tuple[int, str]] = []
    for match in _CURRENCY_RE.finditer(text):
        number, suffix = match.group(1), (match.group(2) or "")
        number = number.replace(",", ".")
        if re.fullmatch(r"0\d+", number):
            continue
        number = _round_hud_number(number)
        if suffix and suffix[0] in "eE":
            suffix = "e" + suffix[1:]
        else:
            suffix = suffix.upper()
        # Never keep a lone "M" glued from min after a botched sanitize.
        if suffix == "M" and (rate_mode or saw_rate) and "." not in number:
            # Bare "294M" on a /min row is almost never real; prefer treating as 294.
            if len(re.sub(r"\D", "", number)) <= 3:
                suffix = ""
        token = f"{number}{suffix}"
        scored.append(
            (_score_currency_token(number, suffix, rate_mode=rate_mode, saw_rate=saw_rate), token)
        )
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _accept_contract(value: str, contract: re.Pattern[str]) -> str:
    if value and contract.fullmatch(value):
        return value
    return ""


def _accept_balance_token(token: str) -> str:
    """HUD balances with KMBT are at most 999.99X — reject OCR monsters like 270860K."""

    if not token:
        return ""
    if re.search(r"[KMBT]$", token, re.I):
        if not re.fullmatch(r"\d{1,3}(?:\.\d{1,2})?[KMBT]", token, re.I):
            return ""
    return _accept_contract(token, _BALANCE_CONTRACT)


def parse_currency(raw: str) -> str:
    """General Tower quantity (legacy). Sanitizes /min → m. Prefer typed parse_as."""

    text, saw_rate = _prep_currency_text(raw, rate_mode=False)
    token = _pick_currency_token(text, rate_mode=saw_rate, saw_rate=saw_rate)
    return _accept_balance_token(token)


def parse_currency_balance(raw: str) -> str:
    """Coin/cash balances: 11.28K, 8.61K, 431. Abstain if contract fails."""

    text, saw_rate = _prep_currency_text(raw, rate_mode=False)
    token = _pick_currency_token(text, rate_mode=False, saw_rate=saw_rate)
    return _accept_balance_token(token)


def parse_currency_rate(raw: str) -> str:
    """Per-minute rates. Plain 1–3 digit ints OK; never invent millions from /min."""

    text, saw_rate = _prep_currency_text(raw, rate_mode=True)
    token = _pick_currency_token(text, rate_mode=True, saw_rate=True)
    if not token:
        return ""
    # Extra rate guard: plain ints must be 1–3 digits (142/min, not 1472).
    if re.fullmatch(r"\d{4,}", token):
        return ""
    # Decimals without K are almost always /min-noise (14.72 from 1472m).
    if "." in token and not re.search(r"[K]$", token, re.I):
        return ""
    # M/B on a /min row is never a real Tower rate magnitude.
    if re.search(r"[MB]$", token, re.I):
        return ""
    return _accept_contract(token, _RATE_CONTRACT)


def parse_currency_int(raw: str) -> str:
    """Plain gem/diamond counts (2–4 digits). No KMBT inventing."""

    text = (raw or "").replace(",", "")
    # Magnitude *suffix* belongs on balance/rate fields (not a leading icon letter).
    if re.search(r"\d\s*[KMBT]\b", text, flags=re.IGNORECASE):
        return ""
    text, _ = sanitize_rate_unit_noise(text)
    # Icon letter glued on: "m546" → "546"
    text = re.sub(r"^[^\d]+", "", text.strip())
    candidates = re.findall(r"(?<!\d)(\d{2,4})(?!\d)", text)
    if not candidates:
        return ""
    # Prefer a 3-digit reading when several intact numbers appear (icon bleed).
    threes = [c for c in candidates if len(c) == 3]
    if threes:
        return _accept_contract(threes[0], _INT_CONTRACT)
    twos = [c for c in candidates if len(c) == 2]
    if twos and not any(len(c) == 4 for c in candidates):
        return _accept_contract(twos[0], _INT_CONTRACT)
    fours = [c for c in candidates if len(c) == 4]
    if fours:
        return _accept_contract(fours[0], _INT_CONTRACT)
    return _accept_contract(candidates[0], _INT_CONTRACT)


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
    if parse_as == "currency_balance":
        return parse_currency_balance(raw)
    if parse_as == "currency_rate":
        return parse_currency_rate(raw)
    if parse_as == "currency_int":
        return parse_currency_int(raw)
    if parse_as == "game_over":
        return parse_game_over(raw)
    if parse_as == "presence":
        return parse_presence(raw)
    return raw


# Thin HUD digits that Tesseract swaps. Used to prefer threshold / abstain.
_DIGIT_CONFUSIONS = frozenset(
    {
        ("1", "7"),
        ("7", "1"),
        ("2", "7"),
        ("7", "2"),
        ("2", "8"),
        ("8", "2"),
        ("3", "8"),
        ("8", "3"),
        ("5", "6"),
        ("6", "5"),
    }
)


@dataclass(frozen=True)
class _Attempt:
    raw: str
    inference: str
    score: int
    prep: str
    used_threshold: bool


def _single_digit_confusion(a: str, b: str) -> bool:
    """True when a/b are same length and differ by one known-confused digit."""

    if not a or not b or len(a) != len(b):
        return False
    diffs = [(x, y) for x, y in zip(a, b) if x != y]
    return len(diffs) == 1 and diffs[0] in _DIGIT_CONFUSIONS


def _attempt_base_score(parse_as: str, raw: str, inference: str) -> int:
    if not inference:
        return -100
    if parse_as == "wave":
        return 100 if _WAVE_LABELED_RE.search(raw or "") else 10
    if parse_as == "currency_int":
        score = 20 + len(inference)
        if len(inference) == 3:
            score += 15
        if re.fullmatch(r"\d{2,4}", inference):
            score += 10
        return score
    if parse_as in _CURRENCY_FAMILY:
        score = len(re.sub(r"\D", "", inference))
        if re.search(r"[KMBT]$", inference, re.I):
            score += 10
        if "." in inference:
            score += 25
        elif re.search(r"\.\d", raw or ""):
            score -= 30
        if re.fullmatch(r"\d{1,3}\.\d{1,2}[KMBT]", inference, re.I):
            score += 20
        if re.search(r"(?<![\d.])\d{1,3}\.\d{1,2}\s*[KMBT]\b", raw or "", re.I):
            score += 12
        if re.fullmatch(r"\d{3,6}", inference):
            score += 18
        if re.search(r"/\s*min", raw or "", re.I):
            score += 5
        if parse_as == "currency_rate" and re.fullmatch(r"\d{1,3}", inference):
            score += 12
        if inference.startswith("0."):
            score -= 25
        if re.fullmatch(r"[A-Za-z]+", inference):
            return -5
        digits_only = re.sub(r"\D", "", inference)
        if len(digits_only) <= 2 and not re.search(r"[KMBT]$", inference, re.I):
            score -= 15
        if re.fullmatch(r"\d{1,2}[KMBT]", inference, re.I) and "." not in inference:
            score -= 10
        # Bare mid rates like 29K/30K are usually icon bleed, not HUD truth.
        if parse_as == "currency_rate" and re.fullmatch(r"\d{2,3}[KMBT]", inference, re.I):
            score -= 20
        if parse_as == "currency_rate" and re.search(r"[MB]$", inference, re.I):
            score -= 50
        return score
    return 1


def _majority(values: list[str]) -> tuple[str, int]:
    if not values:
        return "", 0
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    winner = max(counts.items(), key=lambda item: (item[1], len(item[0])))
    return winner[0], winner[1]


def _select_attempt(parse_as: str, attempts: list[_Attempt]) -> tuple[_Attempt | None, dict[str, Any]]:
    """Pick a winner across preps. Prefer agreement + threshold over first-equal-wins."""

    meta: dict[str, Any] = {"parse_as": parse_as, "attempts": len(attempts)}
    viable = [a for a in attempts if a.inference]
    if not viable:
        return None, meta

    if parse_as == "currency_int":
        threes = [a for a in viable if len(a.inference) == 3]
        pool = threes or viable
        threshold_pool = [a for a in pool if a.used_threshold]
        if threshold_pool:
            th_vals = [a.inference for a in threshold_pool]
            winner, count = _majority(th_vals)
            if count >= 1:
                # Prefer threshold consensus — fixes 816 vs 216 when non-th majority lies.
                chosen = next(a for a in threshold_pool if a.inference == winner)
                meta["select"] = "threshold_majority"
                meta["votes"] = {v: th_vals.count(v) for v in sorted(set(th_vals))}
                return chosen, meta
        vals = [a.inference for a in pool]
        winner, count = _majority(vals)
        unique = sorted(set(vals))
        if len(unique) >= 2:
            top = sorted(((vals.count(v), v) for v in unique), reverse=True)
            if top[0][0] == top[1][0] and _single_digit_confusion(top[0][1], top[1][1]):
                meta["select"] = "abstain_confusion"
                meta["votes"] = {v: vals.count(v) for v in unique}
                return None, meta
            if (
                top[0][0] < top[1][0] * 2
                and _single_digit_confusion(top[0][1], top[1][1])
                and not threshold_pool
            ):
                meta["select"] = "abstain_confusion"
                meta["votes"] = {v: vals.count(v) for v in unique}
                return None, meta
        chosen = next(a for a in pool if a.inference == winner)
        meta["select"] = "majority"
        meta["votes"] = {v: vals.count(v) for v in sorted(set(vals))}
        return chosen, meta

    # Balance / rate / legacy currency: score + vote + threshold bonus.
    vote_counts: dict[str, int] = {}
    for attempt in viable:
        vote_counts[attempt.inference] = vote_counts.get(attempt.inference, 0) + 1

    ranked: list[tuple[int, _Attempt]] = []
    for attempt in viable:
        bonus = vote_counts[attempt.inference] * 8
        if attempt.used_threshold:
            bonus += 18
        # HUD-shaped rates/balances get an extra nudge.
        if re.fullmatch(r"\d{1,3}\.\d{1,2}[KMBT]", attempt.inference, re.I):
            bonus += 10
        ranked.append((attempt.score + bonus, attempt))
    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best = ranked[0]
    meta["votes"] = dict(sorted(vote_counts.items()))

    if parse_as == "currency_rate":
        hudish = [
            a
            for a in viable
            if re.fullmatch(r"\d{1,3}\.\d{1,2}[KMBT]", a.inference, re.I)
            or re.fullmatch(r"\d{2,3}", a.inference)  # early-game plains; reject 1-digit clips
        ]
        if not hudish:
            # Fall back to 1-digit plains only when nothing better exists.
            hudish = [a for a in viable if re.fullmatch(r"\d{1,3}", a.inference)]
        if not hudish:
            # No attempt looks like a real /min HUD value — abstain.
            meta["select"] = "abstain_no_hud_shape"
            return None, meta
        hud_list = [a.inference for a in hudish]
        hud_votes: dict[str, int] = {}
        for value in hud_list:
            hud_votes[value] = hud_votes.get(value, 0) + 1
        th_hudish = [a for a in hudish if a.used_threshold]
        th_list = [a.inference for a in th_hudish]
        th_votes: dict[str, int] = {}
        for value in th_list:
            th_votes[value] = th_votes.get(value, 0) + 1
        meta["votes"] = hud_votes

        decimal_forms = [
            v for v in hud_votes if re.fullmatch(r"\d{1,3}\.\d{1,2}[KMBT]", v, re.I)
        ]

        def _pick_rate_value(values: list[str], pool: list[_Attempt]) -> _Attempt | None:
            if not values or not pool:
                return None
            # Collapse precision near-duplicates (2.3K + 2.39K) before voting.
            clusters: list[list[str]] = []
            for value in values:
                placed = False
                for cluster in clusters:
                    if any(_rate_near_duplicate(value, other) for other in cluster):
                        cluster.append(value)
                        placed = True
                        break
                if not placed:
                    clusters.append([value])
            best_cluster = max(
                clusters,
                key=lambda cluster: (
                    sum(hud_votes.get(v, 0) for v in cluster),
                    sum(th_votes.get(v, 0) for v in cluster),
                    max(len(v) for v in cluster),
                ),
            )
            pick = max(
                best_cluster,
                key=lambda v: (th_votes.get(v, 0), hud_votes.get(v, 0), len(v)),
            )
            return max(
                (a for a in pool if a.inference == pick),
                key=lambda a: (a.used_threshold, a.score),
            )

        # Prefer threshold-backed decimal rates when any exist (2.39K over 6.93K).
        th_decimals = [
            v for v in th_votes if re.fullmatch(r"\d{1,3}\.\d{1,2}[KMBT]", v, re.I)
        ]
        if th_decimals:
            chosen = _pick_rate_value(th_decimals, th_hudish)
            if chosen is not None:
                meta["select"] = "rate_threshold_decimal"
                return chosen, meta

        if decimal_forms:
            chosen = _pick_rate_value(decimal_forms, hudish)
            if chosen is not None:
                # Require at least some agreement unless threshold-backed.
                if hud_votes[chosen.inference] >= 2 or chosen.used_threshold:
                    meta["select"] = "rate_decimal_cluster"
                    return chosen, meta
            if max(hud_votes[v] for v in decimal_forms) < 2:
                meta["select"] = "abstain_rate_disagreement"
                return None, meta

        hud_winner, _hud_count = _majority(hud_list)
        chosen = max(
            (a for a in hudish if a.inference == hud_winner),
            key=lambda a: (a.used_threshold, a.score, vote_counts[a.inference]),
        )
        meta["select"] = "rate_hud_majority"
        return chosen, meta

    if parse_as in {"currency_balance", "currency"}:
        # Prefer nostrip readings — aggressive strips clip leading digits (208.6→8.6).
        nostrip = [a for a in viable if a.prep.startswith("nostrip/")]
        if nostrip:
            # Drop truncated suffixes of a longer nostrip candidate (8.6K vs 208.6K).
            nostrip_vals = {a.inference for a in nostrip}
            filtered = [
                a
                for a in nostrip
                if not any(
                    a.inference != other
                    and _is_truncated_currency(a.inference, other)
                    for other in nostrip_vals
                )
            ] or nostrip
            # Digit-confusion (11.28K vs 11.78K): prefer nostrip+threshold.
            confusable = [
                a
                for a in filtered
                if any(
                    _single_digit_confusion(
                        re.sub(r"[^\d.]", "", a.inference),
                        re.sub(r"[^\d.]", "", b.inference),
                    )
                    for b in filtered
                    if b.inference != a.inference
                )
            ]
            if confusable:
                th = [a for a in confusable if a.used_threshold] or confusable
                chosen = max(
                    th,
                    key=lambda a: (
                        a.used_threshold,
                        a.score + vote_counts[a.inference] * 4,
                    ),
                )
                meta["select"] = "balance_nostrip_confusion"
                return chosen, meta
            chosen = max(
                filtered,
                key=lambda a: (
                    a.used_threshold,
                    a.score + vote_counts[a.inference] * 8,
                ),
            )
            # Only take nostrip if it is competitive with the global best.
            if chosen.score + 10 >= best.score or chosen.inference == best.inference:
                meta["select"] = "balance_nostrip"
                return chosen, meta

    meta["select"] = "score_vote"
    return best, meta


def _is_truncated_currency(short: str, longer: str) -> bool:
    """True when short looks like a clipped tail of longer (8.6K vs 208.6K)."""

    def stem(value: str) -> tuple[str, str]:
        match = re.fullmatch(r"(\d+(?:\.\d+)?)([KMBT]?)", value, re.I)
        if not match:
            return value, ""
        return match.group(1), match.group(2).upper()

    s_num, s_suf = stem(short)
    l_num, l_suf = stem(longer)
    if not s_num or not l_num or s_suf != l_suf:
        return False
    return len(l_num) > len(s_num) and l_num.endswith(s_num)


def _rate_near_duplicate(a: str, b: str) -> bool:
    """2.3K vs 2.39K — same magnitude family, precision differs."""

    ma = re.fullmatch(r"(\d{1,3})\.(\d{1,2})([KMBT])", a, re.I)
    mb = re.fullmatch(r"(\d{1,3})\.(\d{1,2})([KMBT])", b, re.I)
    if not ma or not mb:
        return False
    if ma.group(1) != mb.group(1) or ma.group(3).upper() != mb.group(3).upper():
        return False
    da, db = ma.group(2), mb.group(2)
    return da.startswith(db) or db.startswith(da)


def ocr_field(image: Image.Image, parse_as: str = "raw") -> OcrResult:
    """OCR a crop. Currency-family fields try multiple preps; contracts may abstain."""

    is_currency = parse_as in _CURRENCY_FAMILY
    # Icon-heavy diamond / dual-icon rate rows need wider strips.
    if parse_as == "currency_int":
        strip_fractions = (0.0, 0.15, 0.22)
    elif parse_as == "currency_rate":
        # Dual coin+gem icons need strip, but ≥0.30 often clips the leading rate digit.
        strip_fractions = (0.0, 0.15, 0.22, 0.28)
    elif is_currency:
        strip_fractions = (0.0, 0.15, 0.22)
    else:
        strip_fractions = (0.0,)

    # (config, invert, scale, threshold|None, label)
    base_attempts: list[tuple[str, bool, int, int | None, str]] = []
    if parse_as == "wave":
        base_attempts = [
            (f"--psm 7 -c tessedit_char_whitelist={_WAVE_WHITELIST}", False, 3, None, "--psm 7"),
            (f"--psm 7 -c tessedit_char_whitelist={_WAVE_WHITELIST}", True, 3, None, "--psm 7 invert"),
            ("--psm 7", False, 3, None, "--psm 7 plain"),
            ("--psm 7", True, 3, None, "--psm 7 invert"),
        ]
    elif parse_as == "currency_int":
        base_attempts = [
            (f"--psm 7 -c tessedit_char_whitelist={_INT_WHITELIST}", False, 3, None, "s3 int"),
            (f"--psm 7 -c tessedit_char_whitelist={_INT_WHITELIST}", False, 3, 150, "s3 th150"),
            (f"--psm 7 -c tessedit_char_whitelist={_INT_WHITELIST}", False, 3, 180, "s3 th180"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, None, "s3 digits"),
            ("--psm 7", False, 3, None, "s3 plain"),
            (f"--psm 8 -c tessedit_char_whitelist={_INT_WHITELIST}", False, 4, None, "psm8 int"),
            (f"--psm 8 -c tessedit_char_whitelist={_INT_WHITELIST}", False, 4, 150, "psm8 th150"),
        ]
    elif parse_as == "currency_rate":
        base_attempts = [
            (f"--psm 7 -c tessedit_char_whitelist={_RATE_WHITELIST}", False, 3, None, "s3 rate"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, None, "s3 digits"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, 150, "s3 th150"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, 180, "s3 th180"),
            ("--psm 7", False, 3, None, "s3 plain"),
            (f"--psm 7 -c tessedit_char_whitelist={_RATE_WHITELIST}", False, 4, None, "s4 rate"),
            (f"--psm 7 -c tessedit_char_whitelist={_RATE_WHITELIST}", False, 4, 150, "s4 th150"),
            ("--psm 8", False, 4, None, "psm8 plain"),
        ]
    elif is_currency:
        # currency + currency_balance
        base_attempts = [
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, None, "s3 digits"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, 150, "s3 th150"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 3, 180, "s3 th180"),
            (f"--psm 7 -c tessedit_char_whitelist={_CURRENCY_WHITELIST}", False, 3, None, "s3 currency"),
            ("--psm 7", False, 3, None, "s3 plain"),
            (f"--psm 7 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 4, None, "digits+suffix"),
            (f"--psm 8 -c tessedit_char_whitelist={_DIGITS_SUFFIX_WHITELIST}", False, 4, None, "psm8 digits"),
            ("--psm 7", False, 4, None, "plain"),
            ("--psm 8", False, 4, None, "psm8 plain"),
        ]
    else:
        base_attempts = [("--psm 7", False, 3, None, "default")]

    attempts: list[_Attempt] = []
    best_meta: dict[str, Any] = {"parse_as": parse_as}

    if parse_as not in {"wave"} | _CURRENCY_FAMILY:
        best_raw = run_ocr(image)
        best_inference = _infer(parse_as, best_raw)
        if not best_inference:
            best_meta["abstained"] = True
        return OcrResult(observation=best_raw, inference=best_inference, meta=best_meta)

    for strip in strip_fractions:
        work = strip_left_icon(image, strip) if strip > 0 else image
        strip_tag = f"strip{int(strip * 100)}" if strip > 0 else "nostrip"
        for config, invert, scale, threshold, label in base_attempts:
            raw = run_ocr(
                work, config=config, invert=invert, scale=scale, threshold=threshold
            )
            inference = _infer(parse_as, raw)
            score = _attempt_base_score(parse_as, raw, inference)
            attempts.append(
                _Attempt(
                    raw=raw,
                    inference=inference,
                    score=score,
                    prep=f"{strip_tag}/{label}",
                    used_threshold=threshold is not None,
                )
            )
            if parse_as == "wave" and _WAVE_LABELED_RE.search(raw or "") and inference:
                break
        if parse_as == "wave" and any(a.inference for a in attempts):
            break

    chosen, select_meta = _select_attempt(parse_as, attempts)
    best_meta.update(select_meta)
    if chosen is None:
        best_meta["abstained"] = True
        # Keep the highest-scoring raw observation for evidence even when abstaining.
        fallback = max(attempts, key=lambda a: a.score) if attempts else None
        return OcrResult(
            observation=(fallback.raw if fallback else ""),
            inference="",
            meta=best_meta,
        )

    best_meta["prep"] = chosen.prep
    best_meta["abstained"] = False
    return OcrResult(observation=chosen.raw, inference=chosen.inference, meta=best_meta)

