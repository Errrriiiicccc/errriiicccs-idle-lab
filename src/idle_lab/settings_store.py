"""Remember click settings between launches."""

from __future__ import annotations

import json
from pathlib import Path

from idle_lab.models import Settings


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
    return (
        Settings(
            click_method=method,
            focus_before_run=bool(data.get("focus_before_run", True)),
            restore_cursor=bool(data.get("restore_cursor", True)),
            countdown_seconds=int(countdown),
        ),
        None,
    )


def save_settings(path: Path, settings: Settings) -> None:
    payload = {
        "click_method": settings.click_method,
        "focus_before_run": settings.focus_before_run,
        "restore_cursor": settings.restore_cursor,
        "countdown_seconds": settings.countdown_seconds,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
