"""Preview which LCO overlay marks a molecule pack will light up."""

from __future__ import annotations

from idle_lab.automations.schema import Collection, Event
from idle_lab.automations.store import AutomationStore


def _stat_collect_event_id(store: AutomationStore) -> str:
    if "stat_collect" in store.events:
        return "stat_collect"
    return "stat_collect"


def _event_focus_actions(event: Event, *, stat_event_id: str) -> list[str]:
    """Focus tokens for one atom, in run order."""

    out: list[str] = []
    saw_lco = False
    for action in event.actions:
        if action.type != "lco":
            continue
        saw_lco = True
        name = str(action.raw.get("action") or "").strip().lower()
        if name:
            out.append(name)
    if saw_lco:
        return out
    # Sensor atoms (persistent state / legacy OCR stats): one focus beat on the V mark.
    if event.id == stat_event_id:
        return ["stat_collect"]
    kinds = {a.type for a in event.actions}
    sensor_kinds = {"ocr", "tool_export", "log", "csv_append", "set_variable", "wait"}
    if kinds and kinds <= sensor_kinds:
        if "ocr" in kinds or "tool_export" in kinds:
            return ["stat_collect"]
    return out


def preview_molecule_focus_actions(collection: Collection, store: AutomationStore) -> list[str]:
    """Flatten a once-molecule into LCO mark ids (queue order)."""

    stat_id = _stat_collect_event_id(store)
    out: list[str] = []

    def walk(coll: Collection) -> None:
        for child_id in coll.children:
            cid = str(child_id).strip()
            if not cid:
                continue
            event = store.events.get(cid)
            if event is not None:
                out.extend(_event_focus_actions(event, stat_event_id=stat_id))
                continue
            nested = store.collections.get(cid)
            if nested is not None:
                walk(nested)

    walk(collection)
    return out


def focus_token_for_event(event: Event, store: AutomationStore) -> str | None:
    """Single focus mark for a non-LCO atom (e.g. Stat collect). LCO atoms return None."""

    actions = _event_focus_actions(event, stat_event_id=_stat_collect_event_id(store))
    if len(actions) == 1 and actions[0] == "stat_collect":
        return "stat_collect"
    return None
