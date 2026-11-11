"""Atom Create / Edit Deck mode — accordion step authoring + persist for lco/click."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from idle_lab.flight_deck.keymap import FlightDeckKeymap, KeymapNode
from idle_lab.live_control.playbook import ACTUATION_ACTIONS


class AtomCreatePhase(str, Enum):
    IDLE = "idle"
    CREATE = "create"
    EDIT = "edit"


@dataclass
class AtomDraft:
    """In-memory draft for Atom Create — save only when persist path is chosen."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    event_id: str = ""
    title: str = ""

    def add_lco(self, action: str) -> None:
        name = str(action or "").strip().lower()
        if name not in ACTUATION_ACTIONS:
            raise ValueError(f"unknown LOL actuation: {name}")
        self.steps.append(
            {
                "type": "lco",
                "action": name,
                "description": f"Playbook actuation {name}.",
            }
        )

    def add_click(self, *, nx: float = 0.5, ny: float = 0.5) -> None:
        self.steps.append(
            {
                "type": "click",
                "nx": float(nx),
                "ny": float(ny),
                "description": "Normalized click (Atom Create).",
            }
        )

    def clear(self) -> None:
        self.steps.clear()
        self.event_id = ""
        self.title = ""


def atom_create_prompt(*, phase: AtomCreatePhase | str, activate_key: str = "`") -> str:
    key = (activate_key or "`").strip() or "`"
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.EDIT:
        return (
            "Atom Edit (skeleton)\n"
            "Accordion leaves stubbed — Esc leaves edit\n"
            f"{key} = Deactivate"
        )
    return (
        "Atom Create — same accordion grammar as Deck menu\n"
        "B Buys · T Tabs · S Scroll · U Utility · K click · E edit stub\n"
        "Esc = save if path set (needs event id), else warn + exit · no silent save\n"
        f"{key} = Deactivate"
    )


def atom_create_legend(*, phase: AtomCreatePhase | str) -> str:
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.EDIT:
        return "ATOM EDIT · ESC"
    return "ATOM CREATE · ACCORDION · ESC = SAVE/EXIT"


def build_atom_create_keymap(*, step_count: int = 0) -> FlightDeckKeymap:
    """FD-style accordion for Atom Create — letters open sections, digits add steps."""

    n = max(0, int(step_count))
    suffix = f" · {n} step(s)" if n else ""

    def leaf(key: str, label: str, action: dict[str, Any], *, description: str = "") -> KeymapNode:
        return KeymapNode(key=key, label=label, description=description, action=action)

    roots = [
        KeymapNode(
            key="B",
            label=f"Buys{suffix}",
            description="Add a buy-slot LOL step.",
            children=[
                leaf("1", "Buy 1", {"type": "atom_add_lco", "action": "buy_1"}),
                leaf("2", "Buy 2", {"type": "atom_add_lco", "action": "buy_2"}),
                leaf("3", "Buy 3", {"type": "atom_add_lco", "action": "buy_3"}),
                leaf("4", "Buy 4", {"type": "atom_add_lco", "action": "buy_4"}),
                leaf("5", "Buy 5", {"type": "atom_add_lco", "action": "buy_5"}),
                leaf("6", "Buy 6", {"type": "atom_add_lco", "action": "buy_6"}),
            ],
        ),
        KeymapNode(
            key="T",
            label="Tabs",
            description="Add a workshop-tab LOL step.",
            children=[
                leaf("1", "Attack", {"type": "atom_add_lco", "action": "tab_attack"}),
                leaf("2", "Defense", {"type": "atom_add_lco", "action": "tab_defense"}),
                leaf("3", "Utility", {"type": "atom_add_lco", "action": "tab_utility"}),
            ],
        ),
        KeymapNode(
            key="S",
            label="Scroll",
            description="Add scroll / fling LOL steps.",
            children=[
                leaf("1", "Scroll up", {"type": "atom_add_lco", "action": "scroll_up"}),
                leaf("2", "Scroll down", {"type": "atom_add_lco", "action": "scroll_down"}),
                leaf("3", "Fling up", {"type": "atom_add_lco", "action": "fling_up"}),
                leaf("4", "Fling down", {"type": "atom_add_lco", "action": "fling_down"}),
            ],
        ),
        KeymapNode(
            key="U",
            label="Utility",
            description="Claim / refresh / stat collect.",
            children=[
                leaf("1", "Claim gem", {"type": "atom_add_lco", "action": "claim_gem"}),
                leaf("2", "Refresh", {"type": "atom_add_lco", "action": "refresh"}),
                leaf("3", "Stat collect", {"type": "atom_add_lco", "action": "stat_collect"}),
            ],
        ),
        leaf(
            "K",
            "Click center",
            {"type": "atom_add_click"},
            description="Add a normalized center click (drag-place later).",
        ),
        leaf(
            "E",
            "Edit (stub)",
            {"type": "atom_edit_enter"},
            description="Reorder / select not wired yet.",
        ),
    ]
    return FlightDeckKeymap(version=1, roots=roots)


_TOKEN_TO_LCO = {
    "Q": "tab_attack",
    "W": "tab_defense",
    "E": "tab_utility",
    "1": "buy_1",
    "2": "buy_2",
    "3": "buy_3",
    "4": "buy_4",
    "5": "buy_5",
    "6": "buy_6",
    "R": "scroll_up",
    "F": "scroll_down",
    "T": "fling_up",
    "G": "fling_down",
    "C": "claim_gem",
    "B": "refresh",
    "V": "stat_collect",
}


def draft_step_from_token(token: str) -> tuple[str, str] | None:
    """Legacy flat-key helper (tests / fallback). Prefer accordion leaves."""

    key = str(token or "").strip().upper()
    if key == "K":
        return ("click", "center")
    action = _TOKEN_TO_LCO.get(key)
    if action:
        return ("lco", action)
    return None


def slugify_event_id(raw: str) -> str:
    text = str(raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "atom_untitled"


def build_event_payload(*, event_id: str, title: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    eid = slugify_event_id(event_id)
    if not steps:
        raise ValueError("cannot save atom with no steps")
    return {
        "id": eid,
        "title": (title or eid).strip() or eid,
        "version": 1,
        "enabled": False,
        "priority": 50,
        "timing": {"type": "interval", "every_ms": 60000},
        "description": "Authored via Atom Create (Molecule Lab).",
        "notes": "enabled:false by default — Run selected once from Molecule Lab Atom tab.",
        "actions": list(steps),
    }


def save_atom_draft(events_dir: Path, draft: AtomDraft) -> Path:
    if not draft.event_id.strip():
        raise ValueError("needs persist path — set event id before save")
    if not draft.steps:
        raise ValueError("needs at least one step before save")
    events_dir = Path(events_dir)
    events_dir.mkdir(parents=True, exist_ok=True)
    payload = build_event_payload(
        event_id=draft.event_id,
        title=draft.title or draft.event_id,
        steps=draft.steps,
    )
    path = events_dir / f"{payload['id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
