"""LOL actuation ↔ atom representability (Molecule Lab Atom tab)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from idle_lab.automations.schema import Event
from idle_lab.automations.store import AutomationStore
from idle_lab.live_control.playbook import ACTUATION_ACTIONS

# Dedicated thin wrappers we seed when an actuation has zero covering atoms.
WRAPPER_PREFIX = "lco_"

ROUTINE_COVERAGE_ID = "health_damage_claim"
ROUTINE_LABEL = "routine_health_damage_claim (Deck A)"

LOL_ONLY_ROWS: tuple[tuple[str, str], ...] = (
    ("describe", "Hold D — overlay-only; not an atom"),
    ("session_pause", "` pause/resume while LOL armed — session chrome"),
    ("session_enter_exit", "Enter/Esc LOL session — Flight Deck chrome"),
    ("hold_spam_toggle", "Hold-spam / toggle input — atoms are discrete steps"),
    ("molecule_marks", "Molecule mark drag/rebind — composer placement, not event steps"),
)

HANDS_TYPES = frozenset(
    {
        "click",
        "mouse",
        "play_preset",
        "ensure_upgrade_tab",
        "seek_list_top",
        "scroll_list",
        "lco",
        "run_event",
    }
)
SENSE_TYPES = frozenset(
    {
        "ocr",
        "tool_export",
        "detect_panel",
        "match_template",
        "screenshot",
        "decide",
        "wait",
        "wait_until",
    }
)

# Creator can round-trip these today once Atom Create save lands (lco + click).
CREATOR_ACTION_TYPES = frozenset({"lco", "click", "log"})


@dataclass(frozen=True)
class CoverageRow:
    actuation: str
    status: str  # covered | missing | lol_only | routine
    note: str
    atom_ids: tuple[str, ...]


def wrapper_id_for(actuation: str) -> str:
    return f"{WRAPPER_PREFIX}{actuation}"


def actuation_ids() -> tuple[str, ...]:
    return tuple(sorted(ACTUATION_ACTIONS))


def atom_tags(event: Event) -> tuple[str, ...]:
    kinds = {a.type for a in event.actions}
    tags: list[str] = []
    if "lco" in kinds:
        tags.append("lco")
    if kinds & HANDS_TYPES and "lco" not in kinds:
        tags.append("hands")
    elif kinds & HANDS_TYPES and any(k != "lco" for k in kinds & HANDS_TYPES):
        tags.append("hands")
    if kinds & SENSE_TYPES:
        tags.append("sense")
    if not tags:
        tags.append("other")
    return tuple(tags)


def creator_representable(event: Event) -> bool:
    """True when every step is in the Atom Create save vocabulary (lco/click/log)."""

    if not event.actions:
        return False
    return all(a.type in CREATOR_ACTION_TYPES for a in event.actions)


def lco_actions_in_event(event: Event) -> set[str]:
    out: set[str] = set()
    for action in event.actions:
        if action.type != "lco":
            continue
        name = str(action.raw.get("action") or "").strip().lower()
        if name:
            out.add(name)
    return out


def covering_atoms(store: AutomationStore) -> dict[str, list[str]]:
    covered = {aid: [] for aid in actuation_ids()}
    for eid, event in store.events.items():
        for name in lco_actions_in_event(event):
            if name in covered:
                covered[name].append(eid)
        # Persistent-state atom stands in for V / stat_collect without an lco step.
        if eid == "stat_collect" and any(a.type == "tool_export" for a in event.actions):
            covered["stat_collect"].append(eid)
    return covered


def build_coverage_rows(store: AutomationStore) -> list[CoverageRow]:
    covered = covering_atoms(store)
    rows: list[CoverageRow] = []
    for aid in actuation_ids():
        ids = tuple(sorted(set(covered.get(aid, []))))
        if ids:
            note = f"via {', '.join(ids[:3])}" + ("…" if len(ids) > 3 else "")
            rows.append(CoverageRow(actuation=aid, status="covered", note=note, atom_ids=ids))
        else:
            rows.append(
                CoverageRow(
                    actuation=aid,
                    status="missing",
                    note=f"no atom yet — seed {wrapper_id_for(aid)}.json",
                    atom_ids=(),
                )
            )
    routine_ids = (ROUTINE_COVERAGE_ID,) if ROUTINE_COVERAGE_ID in store.events else ()
    rows.append(
        CoverageRow(
            actuation=ROUTINE_LABEL,
            status="covered" if routine_ids else "missing",
            note=(
                f"multi-step atom {ROUTINE_COVERAGE_ID} (not lco/routine_*)"
                if routine_ids
                else f"missing {ROUTINE_COVERAGE_ID}"
            ),
            atom_ids=routine_ids,
        )
    )
    for key, note in LOL_ONLY_ROWS:
        rows.append(
            CoverageRow(actuation=key, status="lol_only", note=note, atom_ids=())
        )
    return rows


def stub_event_payload(actuation: str) -> dict[str, Any]:
    eid = wrapper_id_for(actuation)
    title = actuation.replace("_", " ").title()
    return {
        "id": eid,
        "title": f"LOL · {title}",
        "version": 1,
        "enabled": False,
        "priority": 50,
        "timing": {"type": "interval", "every_ms": 60000},
        "description": f"Thin Live Overlay Lab wrapper: one `lco` step ({actuation}).",
        "notes": "Seeded for Molecule Lab LOL coverage. enabled:false — Start selected runs once.",
        "actions": [
            {
                "type": "lco",
                "action": actuation,
                "description": f"Playbook actuation {actuation}.",
            }
        ],
    }


def write_stub_atom(events_dir: Path, actuation: str) -> Path:
    if actuation not in ACTUATION_ACTIONS:
        raise ValueError(f"unknown LOL actuation: {actuation}")
    events_dir = Path(events_dir)
    events_dir.mkdir(parents=True, exist_ok=True)
    path = events_dir / f"{wrapper_id_for(actuation)}.json"
    path.write_text(json.dumps(stub_event_payload(actuation), indent=2) + "\n", encoding="utf-8")
    return path


def seed_missing_wrappers(store: AutomationStore, events_dir: Path) -> list[Path]:
    """Write dedicated lco_* atoms for actuations with zero coverage."""

    covered = covering_atoms(store)
    written: list[Path] = []
    for aid, ids in covered.items():
        if ids:
            continue
        path = events_dir / f"{wrapper_id_for(aid)}.json"
        if path.exists():
            continue
        written.append(write_stub_atom(events_dir, aid))
    return written


def classify_library(store: AutomationStore) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for eid in sorted(store.events.keys()):
        event = store.events[eid]
        tags = atom_tags(event)
        rows.append(
            {
                "id": eid,
                "title": event.title,
                "enabled": bool(event.enabled),
                "tags": tags,
                "creator_ok": creator_representable(event),
                "lco_actions": sorted(lco_actions_in_event(event)),
            }
        )
    return rows
