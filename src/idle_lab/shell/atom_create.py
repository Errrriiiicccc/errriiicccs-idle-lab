"""Atom Create / Edit Deck mode — first real persist for lco + click."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

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
    if kind is AtomCreatePhase.CREATE:
        return (
            "Atom Create\n"
            "1–6 = buy slot · Q/W/E = tab · R/F scroll · T/G fling · C claim · B refresh · V stat\n"
            "K = add click at center · Esc = save if path set, else warn + exit\n"
            f"{key} = Deactivate"
        )
    if kind is AtomCreatePhase.EDIT:
        return (
            "Atom Edit (skeleton)\n"
            "W/S = prev/next · R/F = reorder · event chords later\n"
            "Esc = leave edit (save if path set)\n"
            f"{key} = Deactivate"
        )
    return (
        "Atom Create mode\n"
        "C = create · E = edit · Esc = back to menu\n"
        "Save on exit only when event id is set (no silent save)\n"
        f"{key} = Deactivate"
    )


def atom_create_legend(*, phase: AtomCreatePhase | str) -> str:
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.CREATE:
        return "ATOM CREATE · KEYS ADD STEPS · ESC"
    if kind is AtomCreatePhase.EDIT:
        return "ATOM EDIT · W/S R/F · ESC"
    return "ATOM CREATE · C / E · ESC"


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
    """Return (kind, payload) for create-mode keys. kind is lco|click."""

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
