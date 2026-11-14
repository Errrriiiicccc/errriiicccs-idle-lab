"""Phase Map Atom Create — key groups, phases, scrolls, targets → smaller automation atoms.

Scroll defs reuse the same drag action schema as Automation Atom Create (speed, pause,
handles). Targets expand like Attack tab → buys: enter phase + required scrolls + action.
"""

from __future__ import annotations

import json
import re
from typing import Any

from idle_lab.flight_deck.keymap import FlightDeckKeymap, KeymapNode
from idle_lab.shell.atom_create import (
    AtomDraft,
    build_atom_edit_keymap,
    slugify_event_id,
)


# Roles stamped on gesture steps inside a phase-map draft.
ROLE_ENTER_KEY = "enter_key"
ROLE_EXIT_KEY = "exit_key"
ROLE_SCROLL = "scroll_def"
ROLE_TARGET = "target"
ROLE_REGION = "scroll_region"
ROLE_SENSE = "phase_sense"
ROLE_GESTURE = "gesture"  # free actuation still allowed inside the map

GROUP_TYPES = ("overlay_menu", "dock_tabs", "surface_enter", "rail")
TARGET_KINDS = ("action", "buy", "equip", "sense")


def _leaf(key: str, label: str, action: dict[str, Any], *, description: str = "") -> KeymapNode:
    return KeymapNode(key=key, label=label, description=description, action=action)


def _slug(raw: str) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"


def build_atom_kind_keymap() -> FlightDeckKeymap:
    """First screen of Atom Create — choose core atom kind."""

    return FlightDeckKeymap(
        version=1,
        roots=[
            _leaf(
                "1",
                "Automation",
                {"type": "atom_kind_automation"},
                description="Gesture / action sequence (click, drag, key, OCR, playbook).",
            ),
            _leaf(
                "2",
                "Phase map",
                {"type": "atom_kind_phase_map"},
                description="Screen phases: key groups, scrolls, targets that expand to atoms.",
            ),
        ],
    )


def _phase_hotkey_children(draft: AtomDraft) -> list[KeymapNode]:
    """H Phases leaves — pickers are nested hotkeys, not type-in dialogs."""

    phases = list(draft.phases)
    active = draft.active_phase or ""
    home = draft.home_phase or ""

    def phase_leaves(*, action_type: str, include_root: bool = False, exclude_id: str = "") -> list[KeymapNode]:
        nodes: list[KeymapNode] = []
        if include_root:
            nodes.append(
                _leaf(
                    "0",
                    "(root / none)",
                    {"type": action_type, "phase_id": ""},
                    description="Clear parent — this phase sits at the top.",
                )
            )
        if not phases:
            nodes.append(
                _leaf(
                    "1",
                    "(no phases yet)",
                    {"type": "pm_new_phase"},
                    description="Create a phase first.",
                )
            )
            return nodes
        digit = 1
        for p in phases:
            pid = str(p.get("id") or "")
            if not pid or pid == exclude_id:
                continue
            if digit > 9:
                break
            label = str(p.get("label") or pid)
            marks: list[str] = []
            if pid == active:
                marks.append("active")
            if pid == home:
                marks.append("home")
            suffix = f" · {'/'.join(marks)}" if marks else ""
            nodes.append(
                _leaf(
                    str(digit),
                    f"{label}{suffix}",
                    {"type": action_type, "phase_id": pid},
                    description=f"Select phase {pid}.",
                )
            )
            digit += 1
        if not nodes and not include_root:
            nodes.append(
                _leaf(
                    "1",
                    "(no other phases)",
                    {"type": "pm_new_phase"},
                    description="Need another phase to pick.",
                )
            )
        return nodes

    return [
        _leaf(
            "1",
            "New phase",
            {"type": "pm_new_phase"},
            description="Name a phase; becomes active for later placements.",
        ),
        KeymapNode(
            key="2",
            label=f"Set active · {active or '(none)'}",
            description="Hotkey-pick which phase new keys/targets/scrolls bind to.",
            children=phase_leaves(action_type="pm_pick_active"),
        ),
        KeymapNode(
            key="3",
            label=f"Set parent of {active or '(none)'}",
            description="Hotkey-pick parent for the active phase (0 = root).",
            children=phase_leaves(
                action_type="pm_pick_parent",
                include_root=True,
                exclude_id=active,
            ),
        ),
        KeymapNode(
            key="4",
            label=f"Mark home · {home or '(none)'}",
            description="Hotkey-pick the default surface this map opens into.",
            children=phase_leaves(action_type="pm_pick_home"),
        ),
    ]


def build_phase_map_keymap(*, draft: AtomDraft) -> FlightDeckKeymap:
    """Comprehensive Phase Map Create leaves for menu navigation (Cards, shops, tabs)."""

    n = len(draft.steps)
    phase = draft.active_phase or "(no phase)"
    group = draft.active_group or "(no group)"
    gtype = draft.active_group_type or "overlay_menu"
    suffix = f" · {n} piece(s)" if n else ""
    phase_n = len(draft.phases)

    return FlightDeckKeymap(
        version=1,
        roots=[
            KeymapNode(
                key="G",
                label=f"Key Group · {group}",
                description="Related menu keys that enter/exit phases (burger rail, footer tabs).",
                children=[
                    _leaf(
                        "1",
                        "New group",
                        {"type": "pm_new_group"},
                        description="Name a key group (e.g. options_rail, footer_tabs).",
                    ),
                    _leaf(
                        "2",
                        f"Type: {gtype}",
                        {"type": "pm_cycle_group_type"},
                        description="overlay_menu · dock_tabs · surface_enter · rail",
                    ),
                    _leaf(
                        "3",
                        "Enter key (click)",
                        {"type": "pm_add_enter_key"},
                        description="Place click → enters the active phase (Cards icon, Attack tab).",
                    ),
                    _leaf(
                        "4",
                        "Exit key (click)",
                        {"type": "pm_add_exit_key"},
                        description="Place click → leaves phase (X, Tap To Return, chevron).",
                    ),
                    _leaf(
                        "5",
                        "Enter key (hotkey)",
                        {"type": "pm_add_enter_key_hotkey"},
                        description="Same as enter, but capture a keyboard chord (Q/W/E…).",
                    ),
                ],
            ),
            KeymapNode(
                key="H",
                label=f"Phases · {phase} ({phase_n})",
                description="Named screen modes this map owns (cards, shop, upgrade_attack).",
                children=_phase_hotkey_children(draft),
            ),
            KeymapNode(
                key="T",
                label=f"Targets{suffix}",
                description="Things available IN a phase — cards, buy rows, sense checks.",
                children=[
                    _leaf(
                        "1",
                        "Action / Equip (click)",
                        {"type": "pm_add_target", "target_kind": "equip"},
                        description="e.g. Free Upgrades tile — expands to enter+scrolls+click.",
                    ),
                    _leaf(
                        "2",
                        "Buy (click)",
                        {"type": "pm_add_target", "target_kind": "buy"},
                        description="Buy button in-phase; Edit gets Single/Spam like Automation.",
                    ),
                    _leaf(
                        "3",
                        "Action (click)",
                        {"type": "pm_add_target", "target_kind": "action"},
                        description="Generic in-phase tap (info, claim, toggle).",
                    ),
                    _leaf(
                        "4",
                        "Sense (OCR)",
                        {"type": "pm_add_target", "target_kind": "sense"},
                        description="Prove state in-phase (equipped checkmark, title CARDS).",
                    ),
                    _leaf(
                        "5",
                        "Bind scrolls → target",
                        {"type": "pm_bind_scrolls"},
                        description="Attach named scroll defs to the selected target (order preserved).",
                    ),
                ],
            ),
            KeymapNode(
                key="S",
                label="Scroll defs",
                description="Same drag engine as Automation — amount/direction via handles; Edit = Speed/Pause.",
                children=[
                    _leaf(
                        "1",
                        "Place scroll (drag)",
                        {"type": "pm_add_scroll"},
                        description="Identical to Automation Drag: start+end handles on the game.",
                    ),
                    _leaf(
                        "2",
                        "Name selected scroll",
                        {"type": "pm_name_scroll"},
                        description="e.g. inventory_down — targets bind by this id.",
                    ),
                    _leaf(
                        "3",
                        "Bind scroll → phase",
                        {"type": "pm_bind_scroll_phase"},
                        description="Which phase this scroll is legal in (usually Cards inventory).",
                    ),
                    _leaf(
                        "4",
                        "Link scroll → region",
                        {"type": "pm_link_scroll_region"},
                        description="Optional: which viewport ROI the drag belongs to.",
                    ),
                ],
            ),
            KeymapNode(
                key="R",
                label="Regions / Sense",
                description="Panel geometry and prove-you're-here cues.",
                children=[
                    _leaf(
                        "1",
                        "Scroll viewport (ROI)",
                        {"type": "pm_add_region"},
                        description="Inventory / list bounds — where scrolls apply.",
                    ),
                    _leaf(
                        "2",
                        "Phase sense (OCR)",
                        {"type": "pm_add_phase_sense"},
                        description="Title/banner cue that confirms the phase (CARDS header).",
                    ),
                    _leaf(
                        "3",
                        "Active strip (ROI)",
                        {"type": "pm_add_region", "region_kind": "active_strip"},
                        description="e.g. ACTIVE 7/7 card row — separate from inventory scroll.",
                    ),
                ],
            ),
            KeymapNode(
                key="A",
                label="Actuation (raw)",
                description="Same Basic Gesture palette — results unify with Automation atoms.",
                children=[
                    _leaf(
                        "1",
                        "Click",
                        {"type": "pm_add_gesture", "gesture": "click"},
                        description="Free click tagged as gesture (rare; prefer Key Group / Target).",
                    ),
                    _leaf(
                        "2",
                        "Drag",
                        {"type": "pm_add_gesture", "gesture": "drag"},
                        description="Free drag — prefer Scroll defs for list motion.",
                    ),
                    _leaf(
                        "3",
                        "Key",
                        {"type": "pm_add_gesture", "gesture": "key"},
                        description="Raw key send (same capture flow as Automation).",
                    ),
                    _leaf(
                        "4",
                        "OCR",
                        {"type": "pm_add_gesture", "gesture": "ocr"},
                        description="Raw OCR region (same as Automation).",
                    ),
                ],
            ),
            _leaf(
                "E",
                "Edit",
                {"type": "atom_edit_enter"},
                description="Select / reorder / tune. Scroll defs get drag Speed+Pause leaves.",
            ),
            _leaf(
                "X",
                "Expand preview",
                {"type": "pm_expand_preview"},
                description="Show what the selected target becomes as a small automation atom.",
            ),
        ],
    )


def build_phase_map_edit_keymap(
    *,
    step_count: int = 0,
    selected_index: int = 0,
    selected_step: dict[str, Any] | None = None,
) -> FlightDeckKeymap:
    """Edit leaves = Automation edit for the gesture, plus phase-map role leaves."""

    base = build_atom_edit_keymap(
        step_count=step_count,
        selected_index=selected_index,
        selected_step=selected_step,
    )
    step = selected_step or {}
    role = str(step.get("role") or "").strip()
    extras: list[KeymapNode] = []
    if role:
        extras.append(
            _leaf(
                "P",
                f"Role: {role}",
                {"type": "pm_edit_show_role"},
                description="Phase-map role on this piece (informational).",
            )
        )
    if role == ROLE_TARGET:
        scrolls = step.get("scrolls") or []
        extras.append(
            _leaf(
                "B",
                f"Scrolls: {len(scrolls)}",
                {"type": "pm_bind_scrolls"},
                description="Rebind scroll defs required before this target.",
            )
        )
        extras.append(
            _leaf(
                "N",
                f"Name: {step.get('label') or step.get('target_id') or '?'}",
                {"type": "pm_rename_selected"},
                description="Rename target (molecule palette label).",
            )
        )
    if role == ROLE_SCROLL:
        extras.append(
            _leaf(
                "N",
                f"Scroll id: {step.get('scroll_id') or '?'}",
                {"type": "pm_name_scroll"},
                description="Rename scroll def id.",
            )
        )
    # Insert extras before trailing "Back to Create" (last root).
    if extras and base.roots:
        base.roots = list(base.roots[:-1]) + extras + [base.roots[-1]]
    return base


def ensure_phase_map_defaults(draft: AtomDraft) -> None:
    draft.kind = "phase_map"
    if not draft.phases:
        draft.phases = []
    if not draft.active_group_type:
        draft.active_group_type = "overlay_menu"


def add_enter_key(draft: AtomDraft, *, via: str = "click") -> None:
    ensure_phase_map_defaults(draft)
    phase = draft.active_phase or "unnamed"
    group = draft.active_group or "ungrouped"
    if via == "key":
        draft.add_key("?", pending=True)
    else:
        draft.add_click()
    step = draft.steps[draft.selected_index]
    step["role"] = ROLE_ENTER_KEY
    step["phase"] = phase
    step["group"] = group
    step["group_type"] = draft.active_group_type
    step["label"] = step.get("label") or f"enter:{phase}"
    step["description"] = f"Phase map enter → {phase} (group {group})."


def add_exit_key(draft: AtomDraft) -> None:
    ensure_phase_map_defaults(draft)
    phase = draft.active_phase or "unnamed"
    group = draft.active_group or "ungrouped"
    draft.add_click()
    step = draft.steps[draft.selected_index]
    step["role"] = ROLE_EXIT_KEY
    step["phase"] = phase
    step["group"] = group
    step["leaves_phase"] = phase
    step["label"] = step.get("label") or f"exit:{phase}"
    step["description"] = f"Phase map exit ← {phase}."


def add_scroll_def(draft: AtomDraft) -> None:
    """Scroll = Automation drag under the hood."""

    ensure_phase_map_defaults(draft)
    draft.add_drag()
    step = draft.steps[draft.selected_index]
    sid = f"scroll_{len([s for s in draft.steps if s.get('role') == ROLE_SCROLL])}"
    step["role"] = ROLE_SCROLL
    step["scroll_id"] = sid
    step["phase"] = draft.active_phase or ""
    step["label"] = sid
    step["description"] = "Phase map scroll def (drag — same fields as Automation)."


def add_target(draft: AtomDraft, *, target_kind: str = "equip") -> None:
    ensure_phase_map_defaults(draft)
    kind = target_kind if target_kind in TARGET_KINDS else "action"
    if kind == "sense":
        draft.add_ocr()
    else:
        draft.add_click()
    step = draft.steps[draft.selected_index]
    tid = f"target_{len([s for s in draft.steps if s.get('role') == ROLE_TARGET])}"
    step["role"] = ROLE_TARGET
    step["target_kind"] = kind
    step["target_id"] = tid
    step["label"] = tid
    step["phase"] = draft.active_phase or ""
    step["scrolls"] = []
    step["description"] = f"Phase map target ({kind}) in phase {step['phase'] or '?'}."


def add_region(draft: AtomDraft, *, region_kind: str = "scroll_viewport") -> None:
    ensure_phase_map_defaults(draft)
    draft.add_ocr()
    step = draft.steps[draft.selected_index]
    rid = f"region_{len([s for s in draft.steps if s.get('role') == ROLE_REGION])}"
    step["role"] = ROLE_REGION
    step["region_id"] = rid
    step["region_kind"] = region_kind
    step["phase"] = draft.active_phase or ""
    step["ocr_kind"] = "shape"
    step["needs_review"] = True
    step["label"] = rid
    step["description"] = f"Phase map region ({region_kind})."


def add_phase_sense(draft: AtomDraft) -> None:
    ensure_phase_map_defaults(draft)
    draft.add_ocr()
    step = draft.steps[draft.selected_index]
    step["role"] = ROLE_SENSE
    step["phase"] = draft.active_phase or ""
    step["label"] = f"sense:{step['phase'] or 'phase'}"
    step["description"] = "Phase discriminant OCR (prove this phase is open)."


def add_raw_gesture(draft: AtomDraft, *, gesture: str) -> None:
    ensure_phase_map_defaults(draft)
    g = str(gesture or "click").strip().lower()
    if g == "drag":
        draft.add_drag()
    elif g == "key":
        draft.add_key("?", pending=True)
    elif g == "ocr":
        draft.add_ocr()
    else:
        draft.add_click()
    step = draft.steps[draft.selected_index]
    step["role"] = ROLE_GESTURE
    step["phase"] = draft.active_phase or ""
    step["description"] = f"Phase map raw {g} (unified Automation result)."


def cycle_group_type(draft: AtomDraft) -> str:
    ensure_phase_map_defaults(draft)
    cur = draft.active_group_type or GROUP_TYPES[0]
    try:
        i = GROUP_TYPES.index(cur)
    except ValueError:
        i = 0
    nxt = GROUP_TYPES[(i + 1) % len(GROUP_TYPES)]
    draft.active_group_type = nxt
    return nxt


def register_phase(draft: AtomDraft, name: str, *, parent: str = "") -> str:
    ensure_phase_map_defaults(draft)
    pid = _slug(name)
    label = str(name or pid).strip() or pid
    existing = next((p for p in draft.phases if p.get("id") == pid), None)
    if existing is None:
        draft.phases.append({"id": pid, "label": label, "parent": _slug(parent) if parent else ""})
    else:
        existing["label"] = label
        if parent:
            existing["parent"] = _slug(parent)
    draft.active_phase = pid
    if not draft.home_phase:
        draft.home_phase = pid
    return pid


def set_parent_phase(draft: AtomDraft, child: str, parent: str) -> None:
    ensure_phase_map_defaults(draft)
    cid = _slug(child) if child else draft.active_phase
    for p in draft.phases:
        if p.get("id") == cid:
            p["parent"] = _slug(parent) if parent else ""
            return
    if cid:
        draft.phases.append({"id": cid, "label": cid, "parent": _slug(parent) if parent else ""})


def phase_enter_chain(draft: AtomDraft, phase_id: str) -> list[dict[str, Any]]:
    """Walk parent links; return enter_key steps from root → phase."""

    by_id = {str(p.get("id")): p for p in draft.phases}
    chain_ids: list[str] = []
    cur = _slug(phase_id)
    seen: set[str] = set()
    while cur and cur not in seen:
        seen.add(cur)
        chain_ids.append(cur)
        parent = str((by_id.get(cur) or {}).get("parent") or "")
        cur = parent
    chain_ids.reverse()
    enters = [s for s in draft.steps if str(s.get("role")) == ROLE_ENTER_KEY]
    ordered: list[dict[str, Any]] = []
    for pid in chain_ids:
        for step in enters:
            if str(step.get("phase") or "") == pid:
                ordered.append(step)
                break
    return ordered


def _action_from_step(step: dict[str, Any]) -> dict[str, Any]:
    """Strip phase-map metadata → runtime Automation action."""

    out = {k: v for k, v in step.items() if k not in {
        "role",
        "group",
        "group_type",
        "phase",
        "leaves_phase",
        "scroll_id",
        "target_id",
        "target_kind",
        "scrolls",
        "region_id",
        "region_kind",
        "label",
        "home",
    }}
    return out


def expand_target_actions(draft: AtomDraft, target_step: dict[str, Any]) -> list[dict[str, Any]]:
    """Attack-tab→buy style: enter chain + bound scrolls + target gesture."""

    phase = str(target_step.get("phase") or draft.active_phase or "")
    actions: list[dict[str, Any]] = []
    for enter in phase_enter_chain(draft, phase):
        actions.append(_action_from_step(enter))
    scroll_ids = [str(s) for s in (target_step.get("scrolls") or [])]
    scrolls = {
        str(s.get("scroll_id") or ""): s
        for s in draft.steps
        if str(s.get("role")) == ROLE_SCROLL
    }
    for sid in scroll_ids:
        step = scrolls.get(sid)
        if step is not None:
            actions.append(_action_from_step(step))
    actions.append(_action_from_step(target_step))
    return actions


def expand_target_event(
    draft: AtomDraft,
    target_step: dict[str, Any],
    *,
    map_id: str,
) -> dict[str, Any]:
    label = str(target_step.get("label") or target_step.get("target_id") or "target")
    tid = _slug(str(target_step.get("target_id") or label))
    mid = slugify_event_id(map_id or draft.event_id or "phase_map")
    event_id = f"{mid}__{tid}"
    actions = expand_target_actions(draft, target_step)
    if not actions:
        raise ValueError("target expand produced no actions")
    return {
        "id": event_id,
        "title": label,
        "version": 1,
        "enabled": False,
        "priority": 50,
        "timing": {"type": "interval", "every_ms": 60000},
        "description": (
            f"Expanded from phase map {mid}: enter → scrolls → {label}."
        ),
        "notes": (
            f"phase={target_step.get('phase')} scrolls={target_step.get('scrolls')}\n"
            "Generated by Phase Map expand (Atom Create)."
        ),
        "kind": "automation",
        "source_phase_map": mid,
        "source_target": tid,
        "actions": actions,
    }


def expand_preview_lines(draft: AtomDraft, target_step: dict[str, Any] | None = None) -> list[str]:
    step = target_step
    if step is None:
        if not draft.steps:
            return ["(empty phase map)"]
        cand = draft.steps[draft.selected_index]
        if str(cand.get("role")) != ROLE_TARGET:
            targets = [s for s in draft.steps if str(s.get("role")) == ROLE_TARGET]
            if not targets:
                return ["Select a Target piece (T) to preview expand."]
            step = targets[-1]
        else:
            step = cand
    actions = expand_target_actions(draft, step)
    label = str(step.get("label") or step.get("target_id") or "target")
    lines = [f"Expand «{label}» → {len(actions)} automation action(s):"]
    for i, act in enumerate(actions, start=1):
        kind = str(act.get("type") or "?")
        if kind == "drag":
            lines.append(
                f"  {i}. scroll/drag ({act.get('nx0')},{act.get('ny0')})→"
                f"({act.get('nx1')},{act.get('ny1')}) speed={act.get('speed')}"
            )
        elif kind == "click":
            lines.append(f"  {i}. click ({act.get('nx')},{act.get('ny')})")
        elif kind == "key":
            lines.append(f"  {i}. key:{act.get('key')}")
        else:
            lines.append(f"  {i}. {kind}")
    return lines


def build_phase_map_payload(draft: AtomDraft) -> dict[str, Any]:
    ensure_phase_map_defaults(draft)
    eid = slugify_event_id(draft.event_id or draft.title or "phase_map")
    targets = [s for s in draft.steps if str(s.get("role")) == ROLE_TARGET]
    return {
        "id": eid,
        "title": (draft.title or eid).strip() or eid,
        "version": 1,
        "enabled": False,
        "priority": 50,
        "timing": {"type": "interval", "every_ms": 60000},
        "kind": "phase_map",
        "description": "Phase map atom — key groups, scrolls, targets (Atom Create).",
        "notes": "Expand targets into automation atoms for Molecule Lab (enter+scroll+act).",
        "home_phase": draft.home_phase or draft.active_phase or "",
        "phases": list(draft.phases),
        "active_group": draft.active_group,
        "active_group_type": draft.active_group_type,
        "pieces": list(draft.steps),
        # Runtime still sees actions for "run map once" smoke = home enter only if present.
        "actions": [
            _action_from_step(s)
            for s in draft.steps
            if str(s.get("role")) == ROLE_ENTER_KEY
            and str(s.get("phase")) == (draft.home_phase or draft.active_phase)
        ][:1],
        "targets": [
            {
                "id": str(t.get("target_id") or ""),
                "label": str(t.get("label") or ""),
                "phase": str(t.get("phase") or ""),
                "kind": str(t.get("target_kind") or "action"),
                "scrolls": list(t.get("scrolls") or []),
            }
            for t in targets
        ],
    }


def save_phase_map_draft(events_dir, draft: AtomDraft, *, expand_targets: bool = True):
    """Persist phase map + optional expanded target automation atoms."""

    from pathlib import Path

    events_dir = Path(events_dir)
    events_dir.mkdir(parents=True, exist_ok=True)
    if not draft.event_id.strip():
        raise ValueError("needs persist path — set event id before save")
    if not draft.steps:
        raise ValueError("needs at least one piece before save")
    payload = build_phase_map_payload(draft)
    path = events_dir / f"{payload['id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    expanded: list[Any] = []
    if expand_targets:
        for step in draft.steps:
            if str(step.get("role")) != ROLE_TARGET:
                continue
            try:
                ev = expand_target_event(draft, step, map_id=payload["id"])
            except ValueError:
                continue
            ep = events_dir / f"{ev['id']}.json"
            ep.write_text(json.dumps(ev, indent=2) + "\n", encoding="utf-8")
            expanded.append(ep)
    return path, expanded


def phase_map_legend() -> str:
    return "PHASE MAP · G KEYS · H PHASES · T TARGETS · S SCROLL · R REGION · A RAW · E EDIT"


def role_glyph(role: str) -> str:
    return {
        ROLE_ENTER_KEY: "→",
        ROLE_EXIT_KEY: "←",
        ROLE_SCROLL: "⌄",
        ROLE_TARGET: "★",
        ROLE_REGION: "▭",
        ROLE_SENSE: "◈",
        ROLE_GESTURE: "·",
    }.get(str(role or ""), "·")


def queue_piece_line(step: dict[str, Any], *, index: int, selected: bool) -> str:
    """One queue row for a phase-map piece (keeps Atom queue feel, role-forward)."""

    mark = "▶" if selected else " "
    role = str(step.get("role") or "")
    glyph = role_glyph(role)
    if role == ROLE_ENTER_KEY:
        body = f"{glyph}enter {step.get('phase') or '?'}"
    elif role == ROLE_EXIT_KEY:
        body = f"{glyph}exit {step.get('phase') or '?'}"
    elif role == ROLE_SCROLL:
        body = f"{glyph}scroll {step.get('scroll_id') or step.get('label') or '?'}"
    elif role == ROLE_TARGET:
        kind = str(step.get("target_kind") or "action")
        label = str(step.get("label") or step.get("target_id") or "?")
        scrolls = list(step.get("scrolls") or [])
        extra = f"  +{','.join(str(s) for s in scrolls)}" if scrolls else ""
        body = f"{glyph}{kind} {label}{extra}"
    elif role == ROLE_REGION:
        body = f"{glyph}region {step.get('region_id') or step.get('region_kind') or '?'}"
    elif role == ROLE_SENSE:
        body = f"{glyph}sense {step.get('phase') or '?'}"
    else:
        kind = str(step.get("type") or "?")
        body = f"{glyph}{kind}"
    phase = str(step.get("phase") or "")
    phase_bit = f"  [{phase}]" if phase and role not in {ROLE_ENTER_KEY, ROLE_EXIT_KEY, ROLE_SENSE} else ""
    return f"{mark} {index + 1}. {body}{phase_bit}"


def format_phase_tree_lines(
    phases: list[dict[str, Any]],
    *,
    home_phase: str = "",
    active_phase: str = "",
) -> list[str]:
    """Indented phase hierarchy for the Atom queue window."""

    if not phases:
        return ["  (no phases yet — H→1 New phase)"]
    by_parent: dict[str, list[dict[str, Any]]] = {}
    ids = {str(p.get("id") or "") for p in phases}
    for p in phases:
        parent = str(p.get("parent") or "")
        if parent and parent not in ids:
            parent = ""
        by_parent.setdefault(parent, []).append(p)

    lines: list[str] = []

    def walk(parent: str, indent: str) -> None:
        for p in by_parent.get(parent, []):
            pid = str(p.get("id") or "")
            label = str(p.get("label") or pid)
            flags: list[str] = []
            if pid == home_phase:
                flags.append("home")
            if pid == active_phase:
                flags.append("active")
            flag = f" · {' · '.join(flags)}" if flags else ""
            connector = "└ " if indent else "· "
            lines.append(f"{indent}{connector}{label}{flag}")
            walk(pid, indent + "  ")

    walk("", "")
    # Orphans already handled via missing-parent → root.
    return lines or ["  (no phases yet — H→1 New phase)"]


def phase_map_prompt(*, activate_key: str = "`") -> str:
    key = (activate_key or "`").strip() or "`"
    return (
        "Phase Map — G Key Group · H Phases · T Targets · S Scroll · R Region · A Raw · E Edit\n"
        "Scroll defs = Automation drag (same Speed/Pause). Targets expand to enter+scroll+act.\n"
        f"Esc = save → Atom Lab · {key} = pause Deck (keeps Create)"
    )
