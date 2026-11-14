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
        # Shape-first Deck top-level / accordion leaves
        "open_lol",
        "open_molecule_lab",
        "open_atom_lab",
        "open_atom_create",
        "open_observation_lab",
        "open_idle_lab",
        "open_settings",
        "remap_activate_key",
        "cycle_boot_surface",
        # Atom Create accordion leaves
        "atom_add_lco",
        "atom_add_click",
        "atom_add_drag",
        "atom_add_key",
        "atom_add_ocr",
        "atom_playbook_enter",
        "atom_edit_enter",
        "atom_edit_exit",
        "atom_edit_prev",
        "atom_edit_next",
        "atom_edit_move_up",
        "atom_edit_move_down",
        "atom_edit_remove",
        "atom_edit_toggle_mode",
        "atom_edit_toggle_spam_by",
        "atom_edit_ask_click_amount",
        "atom_edit_ask_duration",
        "atom_edit_ask_interval",
        "atom_edit_recapture_key",
        "atom_edit_drag_cycle_speed",
        "atom_edit_drag_toggle_pause",
        "atom_edit_ocr_cycle_kind",
        "atom_edit_ocr_color",
        "atom_kind_automation",
        "atom_kind_phase_map",
        # Phase map Atom Create leaves
        "pm_new_group",
        "pm_cycle_group_type",
        "pm_add_enter_key",
        "pm_add_enter_key_hotkey",
        "pm_add_exit_key",
        "pm_new_phase",
        "pm_set_active_phase",
        "pm_set_parent_phase",
        "pm_mark_home",
        "pm_pick_active",
        "pm_pick_parent",
        "pm_pick_home",
        "pm_add_target",
        "pm_bind_scrolls",
        "pm_add_scroll",
        "pm_name_scroll",
        "pm_bind_scroll_phase",
        "pm_link_scroll_region",
        "pm_add_region",
        "pm_add_phase_sense",
        "pm_add_gesture",
        "pm_expand_preview",
        "pm_edit_show_role",
        "pm_rename_selected",
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
    elif kind == "atom_add_lco":
        action_name = str(raw.get("action") or "").strip().lower()
        if not action_name:
            raise ActionError("atom_add_lco requires action")
        out["action"] = action_name
    elif kind == "pm_add_target":
        tk = str(raw.get("target_kind") or "equip").strip().lower()
        out["target_kind"] = tk or "equip"
    elif kind == "pm_add_gesture":
        out["gesture"] = str(raw.get("gesture") or "click").strip().lower() or "click"
    elif kind == "pm_add_region":
        rk = str(raw.get("region_kind") or "scroll_viewport").strip().lower()
        out["region_kind"] = rk or "scroll_viewport"
    elif kind in {"pm_pick_active", "pm_pick_parent", "pm_pick_home"}:
        out["phase_id"] = str(raw.get("phase_id") or "").strip()
    return out
