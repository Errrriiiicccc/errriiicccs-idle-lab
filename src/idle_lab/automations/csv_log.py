"""Append-only CSV run log."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CSV_FIELDS = ("datetime", "run_number", "wave_number")


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
) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "datetime": when or local_now_iso(),
        "run_number": str(run_number),
        "wave_number": str(wave_number),
    }
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return row
