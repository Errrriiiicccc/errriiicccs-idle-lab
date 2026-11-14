"""Durable picks + local 'seen NEW' dismissals for Feel Lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from idle_lab.presets import project_root


def feel_dir() -> Path:
    path = project_root() / "feel"
    path.mkdir(parents=True, exist_ok=True)
    return path


def picks_path() -> Path:
    return feel_dir() / "picks.json"


def seen_path() -> Path:
    return feel_dir() / "seen.json"


def load_picks() -> dict[str, Any]:
    path = picks_path()
    if not path.is_file():
        return {"version": 1, "picks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "picks": {}}
    if not isinstance(data, dict):
        return {"version": 1, "picks": {}}
    picks = data.get("picks")
    if not isinstance(picks, dict):
        data["picks"] = {}
    data.setdefault("version", 1)
    return data


def save_pick(stage_id: str, variant_id: str | None, note: str = "") -> None:
    data = load_picks()
    data["picks"][stage_id] = {
        "variant": variant_id,
        "note": note,
    }
    picks_path().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_main_look_id() -> str | None:
    data = load_picks()
    main = data.get("main_look")
    return str(main) if main else None


def set_main_look(look_id: str) -> None:
    """Pin look as #1 main and keep change_theme pick in sync."""
    data = load_picks()
    data["main_look"] = look_id
    data.setdefault("picks", {})
    data["picks"]["change_theme"] = {"variant": look_id, "note": "main"}
    picks_path().write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_seen() -> set[str]:
    path = seen_path()
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    items = data.get("seen") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return set()
    return {str(x) for x in items}


def mark_seen(new_id: str) -> None:
    seen = load_seen()
    seen.add(new_id)
    seen_path().write_text(
        json.dumps({"version": 1, "seen": sorted(seen)}, indent=2) + "\n",
        encoding="utf-8",
    )
