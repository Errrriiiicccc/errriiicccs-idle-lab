"""Append-only CSV run log."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

CSV_FIELDS = ("datetime", "run_number", "wave_number")
ENDGAME_STATS_FIELDS = (
    "datetime",
    "run_number",
    "wave_number",
    "coins",
    "coins_per_min",
    "cash_per_min",
    "diamonds",
    "game_over",
)


def local_now_iso(tz_name: str = "America/New_York") -> str:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        return datetime.now().astimezone().isoformat(timespec="seconds")
    return datetime.now(tz).isoformat(timespec="seconds")


def append_run_row(
    path: Path,
    *,
    run_number: int | str,
    wave_number: int | str,
    when: str | None = None,
    extras: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    row: dict[str, str] = {
        "datetime": when or local_now_iso(),
        "run_number": str(run_number),
        "wave_number": str(wave_number),
    }
    if extras:
        for key, value in extras.items():
            if key in row:
                continue
            row[key] = "" if value is None else str(value)

    fieldnames = _merge_fieldnames(path, row)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return {name: row.get(name, "") for name in fieldnames}


def _merge_fieldnames(path: Path, row: Mapping[str, str]) -> list[str]:
    """Keep existing header order; append any new columns at the end."""

    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            existing = next(reader, [])
        if existing:
            names = list(existing)
            for key in row:
                if key not in names:
                    names.append(key)
            return names

    names = list(CSV_FIELDS)
    for key in row:
        if key not in names:
            names.append(key)
    return names
