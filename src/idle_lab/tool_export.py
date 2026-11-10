"""Read The Tower ``tool_export.json`` (Rend / emulator cache)."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ToolExportError(RuntimeError):
    """Export file missing, unreadable, or missing required shape."""


# Default map: Idle Lab variable → export top-level key.
# Cash is round earnings (no wallet cash balance in the export). Diamonds ≡ Gems.
DEFAULT_FIELD_MAP: dict[str, str] = {
    "wave_number": "CurrentWave",
    "coins": "Coins",
    "gems": "Gems",
    "diamonds": "Gems",
    "cells": "Cells",
    "stones": "Stones",
    "tokens": "Tokens",
    "bits": "Bits",
    "medals": "Medals",
    "keys": "Keys",
    "tier": "CurrentTier",
    "cash": "CashEarnedThisRound",
    "coins_earned_this_round": "CoinsEarnedThisRound",
    "round_active": "RoundActiveBool",
    "play_time": "PlayTime",
    "exported_at": "ExportedAt",
    "user_name": "UserName",
}


def default_export_path() -> Path:
    """Rend App writes pulls here after BlueStacks ADB extract."""

    appdata = os.environ.get("APPDATA") or ""
    return Path(appdata) / "rendapp" / "emulator-imports" / "toolExport_unknown.json"


def resolve_export_path(path: str | Path | None = None) -> Path:
    if path is None or str(path).strip() == "":
        return default_export_path()
    return Path(path).expanduser()


@dataclass(frozen=True)
class ToolExportSnapshot:
    path: Path
    data: dict[str, Any]
    mtime: float
    age_s: float
    variables: dict[str, Any]


def _format_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return ""
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        # Compact but stable for CSV / decide.
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return text
    if value is None:
        return ""
    return str(value)


def load_tool_export(
    path: str | Path | None = None,
    *,
    field_map: Mapping[str, str] | None = None,
    max_age_s: float | None = None,
) -> ToolExportSnapshot:
    """Load export JSON and project selected keys into Idle Lab variables."""

    resolved = resolve_export_path(path)
    if not resolved.is_file():
        raise ToolExportError(f"tool_export not found: {resolved}")
    try:
        raw_text = resolved.read_text(encoding="utf-8-sig")
        data = json.loads(raw_text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ToolExportError(f"tool_export unreadable: {resolved} ({exc})") from exc
    if not isinstance(data, dict):
        raise ToolExportError(f"tool_export root must be an object: {resolved}")

    mtime = resolved.stat().st_mtime
    age_s = max(0.0, time.time() - mtime)
    if max_age_s is not None and age_s > float(max_age_s):
        raise ToolExportError(
            f"tool_export stale: age {age_s:.0f}s > max_age_s {max_age_s:.0f} ({resolved})"
        )

    mapping = dict(DEFAULT_FIELD_MAP if field_map is None else field_map)
    variables: dict[str, Any] = {}
    for variable, export_key in mapping.items():
        if not variable or not export_key:
            continue
        if export_key not in data:
            variables[variable] = ""
            continue
        variables[variable] = _format_value(data[export_key])

    # Always surface meta for logs / decide even if not in map.
    if "ExportVersion" in data and "export_version" not in variables:
        variables["export_version"] = _format_value(data["ExportVersion"])
    if "DataVersion" in data and "data_version" not in variables:
        variables["data_version"] = _format_value(data["DataVersion"])
    variables["tool_export_path"] = str(resolved)
    variables["tool_export_age_s"] = f"{age_s:.1f}"

    return ToolExportSnapshot(
        path=resolved,
        data=data,
        mtime=mtime,
        age_s=age_s,
        variables=variables,
    )
