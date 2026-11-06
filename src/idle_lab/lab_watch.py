"""Directory mtime fingerprint — badge Refresh when chat edits files on disk."""

from __future__ import annotations

from pathlib import Path


def dir_fingerprint(paths: list[Path]) -> float:
    """Max mtime across files under ``paths`` (best-effort; missing dirs → 0)."""

    latest = 0.0
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        try:
            if root.is_file():
                latest = max(latest, root.stat().st_mtime)
                continue
            for path in root.rglob("*"):
                if path.is_file():
                    try:
                        latest = max(latest, path.stat().st_mtime)
                    except OSError:
                        continue
        except OSError:
            continue
    return latest
