"""Human-readable Basic / Detailed text for events and collections."""

from __future__ import annotations

from typing import Any

from idle_lab.automations.schema import Action, Collection, Event
from idle_lab.automations.store import AutomationStore


def _seconds(ms: int) -> str:
    if ms % 1000 == 0:
        return f"{ms // 1000}s"
    return f"{ms / 1000:.1f}s"


def _action_description(action: Action) -> str:
    raw = action.raw
    explicit = raw.get("description")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return _action_basic(action)


def _action_basic(action: Action) -> str:
    raw = action.raw
    kind = action.type
    if kind == "screenshot":
        prefix = raw.get("prefix") or "shot"
        return f"Take a screenshot of the anchored window (saved as {prefix}_…)."
    if kind == "ocr":
        roi = raw.get("roi") or "?"
        variable = raw.get("variable") or roi
        parse_as = raw.get("parse_as") or "raw"
        return f"Read text from region “{roi}” and store it as {variable} ({parse_as})."
    if kind == "tool_export":
        path = raw.get("path")
        where = f" from {path}" if path else " from the Rend tool_export cache"
        return f"Load persistent Tower state{where} into variables."
    if kind == "decide":
        variable = raw.get("variable") or "signal"
        mode = raw.get("mode") or "contains"
        match_a = raw.get("match_a") or "A"
        explain_a = raw.get("explain_a") or "PATH A"
        explain_b = raw.get("explain_b") or "PATH B"
        return (
            f"Choose a path from {variable}: if it {mode} {match_a!r} → {explain_a}; "
            f"otherwise → {explain_b}."
        )
    if kind in {"mouse", "play_preset"}:
        preset = raw.get("preset") or raw.get("name") or "?"
        return f"Play click preset “{preset}” on the anchored window."
    if kind == "record_clip":
        duration = raw.get("duration_s") or 10
        clip_kind = raw.get("kind") or raw.get("name_prefix")
        if clip_kind:
            return f"Record a {duration}s {clip_kind} video clip of the anchored window."
        return f"Record a {duration}s video clip of the anchored window."
    if kind == "csv_append":
        path = raw.get("path") or "run_log.csv"
        return f"Append a row to the spreadsheet file {path}."
    if kind == "log":
        message = raw.get("message") or ""
        return f"Write to the console: {message}" if message else "Write a console message."
    if kind == "set_variable":
        name = raw.get("name") or "?"
        return f"Set variable {name} to {raw.get('value')!r}."
    if kind == "wait":
        ms = raw.get("ms") or raw.get("wait_ms") or 0
        return f"Wait {ms} ms."
    if kind == "click":
        target = raw.get("target")
        if target:
            return f"Click the {target} control on the anchored window."
        return f"Click at ({raw.get('nx')}, {raw.get('ny')})."
    if kind == "detect_panel":
        return "Observe upgrade-panel status (open/closed + Attack/Defense/Utility tab)."
    if kind == "ensure_upgrade_tab":
        tab = raw.get("tab") or "?"
        return f"Ensure the {tab} upgrade tab is open (skip click if already active — retap would close it)."
    if kind == "seek_list_top":
        look = raw.get("look_for") or raw.get("keyword")
        if look:
            return f"Check whether “{look}” is on the first upgrade row; scroll up if not."
        return "Scroll the upgrade list up until it stops moving (top edge)."
    if kind == "scroll_list":
        direction = raw.get("direction") or "down"
        rows = raw.get("rows") or raw.get("amount") or 1
        return f"Scroll the open upgrade list {direction} by ~{rows} tile row(s) (tab-agnostic)."
    if kind == "run_event":
        event_id = raw.get("event") or raw.get("id") or "?"
        return f"Run atom “{event_id}” inline (shared procedure)."
    if kind == "lco":
        target = raw.get("action") or f"key {raw.get('key') or '?'}"
        times = raw.get("times") or 1
        suffix = f" ×{times}" if times != 1 else ""
        return f"Live Control {target}{suffix} (object map + live buy-grid detection)."
    return f"Run action “{kind}”."


def _action_detailed(action: Action, *, indent: str = "") -> list[str]:
    raw = action.raw
    lines = [f"{indent}{_action_description(action)}"]
    kind = action.type
    if kind == "screenshot":
        prefix = raw.get("prefix") or "shot"
        lines.append(f"{indent}  → writes PNG under runs/screenshots/{prefix}_<timestamp>.png")
    elif kind == "ocr":
        lines.append(f"{indent}  → ROI id: {raw.get('roi')}")
        lines.append(f"{indent}  → variable: {raw.get('variable')}  (parse_as={raw.get('parse_as') or 'raw'})")
        lines.append(f"{indent}  → also keeps {raw.get('variable')}_raw with the OCR string")
    elif kind == "tool_export":
        path = raw.get("path") or "%APPDATA%/rendapp/emulator-imports/toolExport_unknown.json"
        lines.append(f"{indent}  → path: {path}")
        if raw.get("max_age_s") not in (None, ""):
            lines.append(f"{indent}  → max_age_s: {raw.get('max_age_s')}")
        field_map = raw.get("map") or raw.get("fields")
        if isinstance(field_map, dict) and field_map:
            lines.append(f"{indent}  → custom map: {len(field_map)} field(s)")
        else:
            lines.append(f"{indent}  → default map: wave, wallets, tier, round_active, …")
        lines.append(f"{indent}  → sets tool_export_ok / tool_export_age_s")
    elif kind == "decide":
        variable = raw.get("variable") or "signal"
        mode = raw.get("mode") or "contains"
        match_a = raw.get("match_a") or "A"
        lines.append(f"{indent}  Decision rule")
        lines.append(f"{indent}    look at: {variable}")
        lines.append(f"{indent}    if {variable} {mode} {match_a!r} → PATH A")
        lines.append(f"{indent}    otherwise → PATH B")
        lines.append(f"{indent}  Branches in contention")
        lines.append(f"{indent}    PATH A — {raw.get('explain_a') or 'on_a actions'}")
        for nested in raw.get("on_a") or []:
            if isinstance(nested, dict):
                nested_action = Action(type=str(nested.get("type") or "?"), raw=nested)
                lines.extend(_action_detailed(nested_action, indent=indent + "      "))
        lines.append(f"{indent}    PATH B — {raw.get('explain_b') or 'on_b actions'}")
        for nested in raw.get("on_b") or []:
            if isinstance(nested, dict):
                nested_action = Action(type=str(nested.get("type") or "?"), raw=nested)
                lines.extend(_action_detailed(nested_action, indent=indent + "      "))
    elif kind in {"mouse", "play_preset"}:
        lines.append(f"{indent}  → preset file name/id: {raw.get('preset') or raw.get('name')}")
        lines.append(f"{indent}  → clicks use the current Clicker method (foreground/background)")
    elif kind == "record_clip":
        duration = raw.get("duration_s") or 10
        clip_kind = raw.get("kind") or raw.get("name_prefix") or ""
        lines.append(f"{indent}  → duration: {duration}s")
        if clip_kind:
            lines.append(
                f"{indent}  → output: runs/clips/{clip_kind}_run_{{run}}_wave_{{wave}}_{{timestamp}}.mp4"
            )
        else:
            lines.append(f"{indent}  → output: runs/clips/run_{{run_number}}_wave_{{wave_number}}.mp4")
        lines.append(f"{indent}  → wave_number comes from OCR taken just before recording")
        lines.append(f"{indent}  → while recording, lower-priority events are deferred")
    elif kind == "csv_append":
        path = raw.get("path") or "run_log.csv"
        lines.append(f"{indent}  → file: runs/{path}")
        extra = raw.get("fields")
        if isinstance(extra, list) and extra:
            cols = ["datetime", "run_number", "wave_number", *[str(c) for c in extra]]
            lines.append(f"{indent}  → columns: {', '.join(cols)}")
        else:
            lines.append(f"{indent}  → columns: datetime, run_number, wave_number")
    elif kind == "log":
        lines.append(f"{indent}  → level: {raw.get('level') or 'info'}")
        lines.append(f"{indent}  → message template: {raw.get('message')!r}")
    elif kind == "set_variable":
        lines.append(f"{indent}  → {raw.get('name')} = {raw.get('value')!r}")
    elif kind == "wait":
        lines.append(f"{indent}  → ms: {raw.get('ms') or raw.get('wait_ms')}")
    elif kind == "click":
        if raw.get("target"):
            lines.append(f"{indent}  → target: {raw.get('target')}")
        else:
            lines.append(f"{indent}  → nx={raw.get('nx')} ny={raw.get('ny')}")
        lines.append(f"{indent}  → hold_ms: {raw.get('hold_ms') or 70}")
    elif kind == "detect_panel":
        lines.append(f"{indent}  → sets panel_open, upgrade_tab, panel_reason")
        if raw.get("prefix"):
            lines.append(f"{indent}  → status shot prefix: {raw.get('prefix')}")
    elif kind == "ensure_upgrade_tab":
        lines.append(f"{indent}  → tab: {raw.get('tab')}")
        lines.append(f"{indent}  → observe → click only if needed → re-observe")
        lines.append(f"{indent}  → never retaps an already-active tab")
    elif kind == "seek_list_top":
        lines.append(f"{indent}  → look_for: {raw.get('look_for') or raw.get('keyword') or '(unchanged edge)'}")
        lines.append(f"{indent}  → controlled drag up (fraction≈0.10) until OCR match or unchanged")
    elif kind == "scroll_list":
        lines.append(f"{indent}  → direction: {raw.get('direction') or 'down'}")
        lines.append(f"{indent}  → rows: {raw.get('rows') or raw.get('amount') or 1}")
        lines.append(f"{indent}  → playbook drag_fraction≈{raw.get('drag_fraction') or 0.10}")
    elif kind == "run_event":
        lines.append(f"{indent}  → event id: {raw.get('event') or raw.get('id')}")
        lines.append(f"{indent}  → executes that atom’s actions in-process (no new scheduler tick)")
    elif kind == "lco":
        if raw.get("action"):
            lines.append(f"{indent}  → action: {raw.get('action')}")
        else:
            lines.append(f"{indent}  → key: {raw.get('key')} (resolved through the object map hotkeys)")
        lines.append(f"{indent}  → times: {raw.get('times') or 1}")
        lines.append(f"{indent}  → headless LCO session: detects panel + buy grid on first lco step of the atom")
        lines.append(f"{indent}  → sets lco_tab, lco_slots, lco_aligned")
    return lines


def _event_blurb(event: Event) -> str:
    if event.description.strip():
        return event.description.strip()
    if event.notes.strip():
        return event.notes.strip()
    bits = [_action_description(action) for action in event.actions[:3]]
    more = "" if len(event.actions) <= 3 else f" (+{len(event.actions) - 3} more steps)"
    return " ".join(bits) + more


def format_event(event: Event, *, detailed: bool, store: AutomationStore | None = None) -> str:
    del store  # reserved for resolving nested refs later
    every = _seconds(event.every_ms)
    lines = [
        event.title,
        "",
        "Atom — Start selected runs this once (interval only when enabled in a pool).",
        "",
        _event_blurb(event),
        "",
        f"Interval when pooled: every {every} · priority {event.priority}"
        + (" · enabled" if event.enabled else " · disabled"),
    ]
    if not detailed:
        lines.append("")
        lines.append("What it does")
        for index, action in enumerate(event.actions, start=1):
            lines.append(f"{index}. {_action_description(action)}")
            if action.type == "decide":
                lines.append("   Branches in contention:")
                lines.append(f"   • PATH A — {action.raw.get('explain_a') or 'on_a'}")
                lines.append(f"   • PATH B — {action.raw.get('explain_b') or 'on_b'}")
                lines.append(
                    f"   Decided by: {action.raw.get('variable')} "
                    f"{action.raw.get('mode')} {action.raw.get('match_a')!r} → A, else B"
                )
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "Schedule / identity",
            f"  id: {event.id}",
            f"  interval: every {event.every_ms} ms ({every})",
            f"  priority: {event.priority} (higher wins when multiple are due)",
            f"  enabled: {event.enabled}",
            f"  file: {event.path or '—'}",
            "",
            "Exact steps",
        ]
    )
    for index, action in enumerate(event.actions, start=1):
        lines.append(f"{index}. [{action.type}]")
        lines.extend(_action_detailed(action, indent="   "))
    if event.notes.strip() and event.notes.strip() != event.description.strip():
        lines.extend(["", "Author notes", f"  {event.notes.strip()}"])
    return "\n".join(lines)


def _resolve_title(store: AutomationStore, item_id: str) -> str:
    if item_id in store.events:
        return store.events[item_id].title
    if item_id in store.collections:
        return store.collections[item_id].title
    return item_id


def _collection_blurb(collection: Collection) -> str:
    if collection.description.strip():
        return collection.description.strip()
    if collection.notes.strip():
        return collection.notes.strip()
    child_n = len(collection.children)
    branch_n = len(collection.branches)
    if branch_n:
        keys = ", ".join(collection.branches.keys())
        return (
            f"Ordered group of {child_n} item(s). Branches on “{collection.branch_variable}” "
            f"among: {keys}."
        )
    return f"Ordered group of {child_n} event/collection id(s)."


def format_collection(collection: Collection, *, detailed: bool, store: AutomationStore) -> str:
    run_mode = (collection.run or "interval").strip().lower()
    run_hint = (
        "Molecule · run=interval — Start selected opens a timed pool of child atoms."
        if run_mode == "interval"
        else "Molecule · run=once — Start selected runs child atoms serially once."
    )
    lines = [
        collection.title,
        "",
        run_hint,
        "",
        _collection_blurb(collection),
    ]
    if collection.branches:
        lines.extend(
            [
                "",
                "Branches in contention",
                f"Decided by variable: {collection.branch_variable}",
                "Rule: match the variable’s value (case-insensitive) to one of these keys:",
            ]
        )
        for key, child_id in collection.branches.items():
            title = _resolve_title(store, child_id)
            lines.append(f"  • if {collection.branch_variable} = {key!r} → {title} ({child_id})")
        lines.append("  • if no key matches → no branch child is selected")
    if not detailed:
        if collection.children:
            lines.append("")
            lines.append("Includes (in order)")
            for index, child_id in enumerate(collection.children, start=1):
                lines.append(f"{index}. {_resolve_title(store, child_id)}")
        extras = []
        if collection.loop:
            extras.append("loops")
        if collection.stop_when:
            extras.append(f"stops when {collection.stop_when}")
        if extras:
            lines.extend(["", "Also: " + ", ".join(extras)])
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "Identity",
            f"  id: {collection.id}",
            f"  run: {collection.run}",
            f"  loop: {collection.loop}",
            f"  stop_when: {collection.stop_when or '—'}",
            f"  file: {collection.path or '—'}",
            "",
            "Children (order)",
        ]
    )
    if not collection.children:
        lines.append("  (none)")
    for index, child_id in enumerate(collection.children, start=1):
        title = _resolve_title(store, child_id)
        kind = "event" if child_id in store.events else ("collection" if child_id in store.collections else "missing")
        lines.append(f"  {index}. {title}")
        lines.append(f"      id: {child_id}  ({kind})")
        if child_id in store.events:
            child = store.events[child_id]
            lines.append(f"      summary: {_event_blurb(child)}")
        elif child_id in store.collections:
            child_c = store.collections[child_id]
            lines.append(f"      summary: {_collection_blurb(child_c)}")
    if collection.branches:
        lines.extend(
            [
                "",
                "Branch map (exact)",
                f"  branch_variable: {collection.branch_variable}",
            ]
        )
        for key, child_id in collection.branches.items():
            lines.append(f"  {key!r} → {child_id} ({_resolve_title(store, child_id)})")
    if collection.notes.strip() and collection.notes.strip() != collection.description.strip():
        lines.extend(["", "Author notes", f"  {collection.notes.strip()}"])
    return "\n".join(lines)


def list_caption(item: Event | Collection) -> str:
    if isinstance(item, Event):
        text = _event_blurb(item)
    else:
        text = _collection_blurb(item)
    text = " ".join(text.split())
    if len(text) > 72:
        return text[:69] + "…"
    return text
