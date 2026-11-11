"""Flight-deck action catalog — only types the lab can actually run."""

from __future__ import annotations

from typing import Any

# Supported ``action.type`` values in taxonomy.json / flight-deck leaves.
ACTION_TYPES = frozenset(
    {
        "play_preset",  # one-shot Bench preset by name
        "start_event",  # interval Loops event by id (forces that event for the session)
        "start_collection",  # collection pack by id
        "start_enabled_loops",  # every file-enabled event (CUT from Deck catalog)
        "observation_start",  # start Observation session (optional title; default auto)
        "observation_mark",  # bookmark frame (CUT from Deck catalog)
        "observation_end",  # stop Observation
        "live_control_enter",  # Live Control Overlay (playbook hit-targets)
        "live_control_enter_troubleshoot",  # Live Control + Observation evidence session
        "live_control_exit",
        "live_control_toggle",
        "live_control_console_toggle",  # Persist LCO console on/off + open/close window
        "live_control_console_verbosity",  # Cycle events → results → process
        "molecule_composer_open",  # Context-gated molecule authoring UI
        # Shape-first Deck top-level (Phase 0 stubs)
        "open_lol",
        "open_molecule_lab",
        "open_observation_lab",
        "open_settings",
        # Legacy aliases → Observation
        "observe_start",
        "observe_shot",
        "observe_end",
        # Legacy aliases → Live Control Overlay (formerly Manual)
        "manual_enter",
        "manual_enter_troubleshoot",
        "manual_exit",
        "manual_toggle",
    }
)

_ACTION_ALIASES = {
    "observe_start": "observation_start",
    "observe_shot": "observation_mark",
    "observe_end": "observation_end",
    "manual_enter": "live_control_enter",
    "manual_enter_troubleshoot": "live_control_enter_troubleshoot",
    "manual_exit": "live_control_exit",
    "manual_toggle": "live_control_toggle",
}


class ActionError(ValueError):
    """Keymap action is missing fields or uses an unknown type."""


def normalize_action(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ActionError("action must be an object")
    kind = str(raw.get("type") or "").strip()
    if kind not in ACTION_TYPES:
        raise ActionError(f"unsupported action type: {kind!r} (allowed: {sorted(ACTION_TYPES)})")
    kind = _ACTION_ALIASES.get(kind, kind)
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
    elif kind == "observation_start":
        title = str(raw.get("title") or "").strip()
        if title:
            out["title"] = title
    return out
