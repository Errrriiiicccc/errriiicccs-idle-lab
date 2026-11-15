"""Idle Lab skins — product face of Feel Lab looks (default Type → Bracket)."""

from __future__ import annotations

from idle_lab.feel_lab.store import get_main_look_id, set_main_look
from idle_lab.feel_lab.themes import (
    FAMILIES,
    Look,
    default_look,
    look_by_id,
)


def active_look() -> Look:
    """Pinned main look from feel/picks.json, else Type → Bracket."""

    pinned = get_main_look_id()
    if pinned:
        found = look_by_id(pinned)
        if found is not None:
            return found
    return default_look()


def list_skin_choices() -> list[tuple[str, str]]:
    """(look_id, 'Family · Title') for Settings / chrome menus."""

    rows: list[tuple[str, str]] = []
    for family in FAMILIES:
        for look in family.looks:
            rows.append((look.id, f"{family.title} · {look.title}"))
    return rows


def choose_skin(look_id: str) -> Look:
    look = look_by_id(look_id) or default_look()
    set_main_look(look.id)
    return look


def format_key_label(look: Look, key: str, label: str) -> str:
    k = (key or "").strip()
    name = (label or "").strip()
    if look.uppercase:
        name = name.upper()
    fmt = look.key_format
    if fmt == "dot":
        return f"{k} · {name}" if k else name
    if fmt == "bare":
        return f"{k} {name}".strip()
    if fmt == "paren":
        return f"({k}) {name}" if k else name
    # bracket (Type → Bracket default)
    return f"[{k}] {name}" if k else name


__all__ = [
    "Look",
    "active_look",
    "choose_skin",
    "default_look",
    "format_key_label",
    "list_skin_choices",
    "look_by_id",
]
