"""Remember click settings between launches."""

from __future__ import annotations

import json
from pathlib import Path

from idle_lab.flight_deck.keys import DEFAULT_EXPAND_VK
from idle_lab.humanize import HUMANIZE_LEVELS, normalize_level
from idle_lab.lab_mode import normalize_lab_mode
from idle_lab.live_control.console import normalize_verbosity
from idle_lab.models import Settings


def _parse_expand_vk(raw) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_EXPAND_VK
    if value <= 0 or value > 0xFE:
        return DEFAULT_EXPAND_VK
    return value


def _parse_expand_by_anchor(raw) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        title = str(key).strip()
        if not title:
            continue
        out[title] = _parse_expand_vk(value)
    return out


def load_settings(path: Path) -> tuple[Settings, str | None]:
    if not path.exists():
        return Settings(), None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return Settings(), "Settings file was unreadable. Defaults were loaded."
    if not isinstance(data, dict):
        return Settings(), "Settings file was unreadable. Defaults were loaded."
    method = data.get("click_method", "foreground")
    if method not in ("foreground", "background"):
        method = "foreground"
    countdown = data.get("countdown_seconds", 0)
    if countdown not in (0, 1, 3):
        countdown = 0
    humanize = normalize_level(data.get("humanize_level", "off"))
    if humanize not in HUMANIZE_LEVELS:
        humanize = "off"
    lab_mode = normalize_lab_mode(data.get("lab_mode", "auto"))
    trace_level = str(data.get("trace_level", "failure") or "failure").strip().lower()
    if trace_level not in {"off", "failure", "all"}:
        trace_level = "failure"
    geometry = data.get("flight_deck_geometry")
    if geometry is not None:
        geometry = str(geometry).strip() or None
    return (
        Settings(
            click_method=method,
            focus_before_run=bool(data.get("focus_before_run", True)),
            restore_cursor=bool(data.get("restore_cursor", True)),
            countdown_seconds=int(countdown),
            humanize_level=humanize,
            lab_mode=lab_mode,
            trace_level=trace_level,
            flight_deck_expand_vk=_parse_expand_vk(
                data.get("flight_deck_expand_vk", DEFAULT_EXPAND_VK)
            ),
            flight_deck_expand_by_anchor=_parse_expand_by_anchor(
                data.get("flight_deck_expand_by_anchor")
            ),
            flight_deck_geometry=geometry,
            flight_deck_user_hidden=bool(data.get("flight_deck_user_hidden", False)),
            last_anchor_title=(
                str(data.get("last_anchor_title") or "").strip() or None
            ),
            lco_console_enabled=bool(data.get("lco_console_enabled", False)),
            lco_console_verbosity=normalize_verbosity(
                str(data.get("lco_console_verbosity") or "results")
            ),
            lco_console_geometry=(
                str(data.get("lco_console_geometry") or "").strip() or None
            ),
        ),
        None,
    )


def save_settings(path: Path, settings: Settings) -> None:
    payload = {
        "click_method": settings.click_method,
        "focus_before_run": settings.focus_before_run,
        "restore_cursor": settings.restore_cursor,
        "countdown_seconds": settings.countdown_seconds,
        "humanize_level": normalize_level(settings.humanize_level),
        "lab_mode": normalize_lab_mode(settings.lab_mode),
        "trace_level": settings.trace_level if settings.trace_level in {"off", "failure", "all"} else "failure",
        "flight_deck_expand_vk": int(settings.flight_deck_expand_vk or DEFAULT_EXPAND_VK),
        "flight_deck_expand_by_anchor": {
            str(k): int(v) for k, v in (settings.flight_deck_expand_by_anchor or {}).items()
        },
        "flight_deck_geometry": settings.flight_deck_geometry,
        "flight_deck_user_hidden": bool(settings.flight_deck_user_hidden),
        "last_anchor_title": settings.last_anchor_title,
        "lco_console_enabled": bool(settings.lco_console_enabled),
        "lco_console_verbosity": normalize_verbosity(settings.lco_console_verbosity),
        "lco_console_geometry": settings.lco_console_geometry,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
