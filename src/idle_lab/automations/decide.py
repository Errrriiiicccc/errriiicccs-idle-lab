"""Pure A/B (and multi-branch) decision helpers."""

from __future__ import annotations

import re
from typing import Any


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def decide_ab(
    value: Any,
    *,
    match_a: str,
    mode: str = "contains",
    case_insensitive: bool = True,
) -> str:
    """Return ``A`` or ``B`` from an OCR/state value.

    ``mode`` is ``contains``, ``equals``, or ``startswith``.
    ``contains`` uses word-boundary matching so ``A`` does not hit inside ``SIGNAL``.
    """

    text = normalize_text(value)
    needle = normalize_text(match_a)
    flags = re.IGNORECASE if case_insensitive else 0
    if case_insensitive:
        text_cmp = text.lower()
        needle_cmp = needle.lower()
    else:
        text_cmp = text
        needle_cmp = needle

    if not needle_cmp:
        return "B"

    if mode == "equals":
        hit = text_cmp == needle_cmp
    elif mode == "startswith":
        hit = text_cmp.startswith(needle_cmp)
    else:
        pattern = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
        hit = re.search(pattern, text, flags=flags) is not None
    return "A" if hit else "B"


def decide_branch(
    value: Any,
    branches: dict[str, Any],
    *,
    default: str | None = None,
    case_insensitive: bool = True,
) -> str | None:
    """Map a variable onto a branch key using equals (optionally case-insensitive)."""

    text = normalize_text(value)
    if case_insensitive:
        text = text.lower()
    for key, target in branches.items():
        key_cmp = key.lower() if case_insensitive else key
        if text == key_cmp:
            return str(target)
    return default
