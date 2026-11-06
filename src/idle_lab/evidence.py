"""Failure evidence packs under runs/failures/."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image


def failure_pack_dir(runs_dir: Path, *, stamp: str | None = None) -> Path:
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dest = Path(runs_dir) / "failures" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def write_failure_pack(
    runs_dir: Path,
    *,
    error: str,
    meta: dict[str, Any],
    window_image: Image.Image | None = None,
    crop_image: Image.Image | None = None,
    stamp: str | None = None,
) -> Path:
    """Write meta.json + optional PNGs. Returns the pack directory."""

    dest = failure_pack_dir(runs_dir, stamp=stamp)
    payload = {
        "error": error,
        "written_at": datetime.now().isoformat(timespec="seconds"),
        **meta,
    }
    (dest / "meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if window_image is not None:
        window_image.save(dest / "window.png")
    if crop_image is not None:
        crop_image.save(dest / "crop.png")
    return dest
