"""Flight-deck action catalog — only types the lab can actually run."""

from __future__ import annotations

from typing import Any

# Supported ``action.type`` values in taxonomy.json / flight-deck leaves.
ACTION_TYPES = frozenset(
    {
        "play_preset",  # one-shot Bench preset by name
        "start_event",  # interval Loops event by id (forces that event for the session)
        "start_collection",  # collection pack by id
        "start_enabled_loops",  # every file-enabled event
        "observe_start",  # start Observe batch (optional title)
        "observe_shot",  # capture shot with auto title (batch must be active)
        "observe_end",  # end active Observe batch
    }
)


class ActionError(ValueError):
    """Keymap action is missing fields or uses an unknown type."""


def normalize_action(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ActionError("action must be an object")
    kind = str(raw.get("type") or "").strip()
    if kind not in ACTION_TYPES:
        raise ActionError(f"unsupported action type: {kind!r} (allowed: {sorted(ACTION_TYPES)})")
    out: dict[str, Any] = {"type": kind}
    if kind == "play_preset":
        preset = str(raw.get("preset") or "").strip()
        if not preset:
            raise ActionError("play_preset requires preset")
        out["preset"] = preset
    elif kind == "start_event":
        event = str(raw.get("event") or "").strip()
        if not event:
            raise ActionError("start_event requires event id")
        out["event"] = event
    elif kind == "start_collection":
        collection = str(raw.get("collection") or "").strip()
        if not collection:
            raise ActionError("start_collection requires collection id")
        out["collection"] = collection
    elif kind == "observe_start":
        title = str(raw.get("title") or "").strip()
        if title:
            out["title"] = title
    return out
