"""Filename / folder slug helpers for Screen Map batches."""

from __future__ import annotations

import re


def sanitize_slug(text: str, *, fallback: str = "shot") -> str:
    """Turn a human title into a safe path segment.

    Keeps lowercase ASCII letters/digits and hyphens. Empty or punctuation-only
    input returns ``fallback``.
    """

    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return cleaned or fallback


def unique_dir(parent, slug: str):
    """Return ``parent/slug`` or ``parent/slug-2``, ``slug-3``, … if taken."""

    from pathlib import Path

    root = Path(parent)
    candidate = root / slug
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = root / f"{slug}-{index}"
        if not candidate.exists():
            return candidate
        index += 1
