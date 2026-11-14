"""Atom Create / Edit Deck mode — accordion step authoring + persist for lco/gestures."""

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
    KIND = "kind"
    CREATE = "create"
    PLAYBOOK = "playbook"
    PHASE_MAP = "phase_map"
    EDIT = "edit"


@dataclass
class AtomDraft:
    """In-memory draft for Atom Create — save only when persist path is chosen."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    event_id: str = ""
    title: str = ""
    selected_index: int = 0
    # automation | phase_map — chosen at Atom Create kind gate
    kind: str = "automation"
    # Phase-map authoring context (ignored for automation)
    phases: list[dict[str, Any]] = field(default_factory=list)
    active_phase: str = ""
    home_phase: str = ""
    active_group: str = ""
    active_group_type: str = "overlay_menu"

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
        self.selected_index = len(self.steps) - 1

    def add_click(self, *, nx: float = 0.5, ny: float = 0.5) -> None:
        self.steps.append(
            {
                "type": "click",
                "nx": float(nx),
                "ny": float(ny),
                "mode": "single",
                "description": "Normalized click (Atom Create).",
            }
        )
        self.selected_index = len(self.steps) - 1

    def add_drag(
        self,
        *,
        nx0: float = 0.40,
        ny0: float = 0.50,
        nx1: float = 0.60,
        ny1: float = 0.50,
    ) -> None:
        self.steps.append(
            {
                "type": "drag",
                "nx0": float(nx0),
                "ny0": float(ny0),
                "nx1": float(nx1),
                "ny1": float(ny1),
                "speed": "medium",
                "pause_end": False,
                "pause_ms": 200,
                "description": "Normalized drag (Atom Create).",
            }
        )
        self.selected_index = len(self.steps) - 1

    def add_key(self, key: str = "a", *, pending: bool = False) -> None:
        token = "?" if pending else (str(key or "").strip() or "a")
        self.steps.append(
            {
                "type": "key",
                "key": token,
                "mode": "single",
                "pending": bool(pending),
                "description": (
                    "Key capture pending — press a key."
                    if pending
                    else f"Send key {token!r} (Atom Create)."
                ),
            }
        )
        self.selected_index = len(self.steps) - 1

    def add_ocr(
        self,
        *,
        nx: float = 0.35,
        ny: float = 0.35,
        nw: float = 0.30,
        nh: float = 0.12,
        variable: str = "ocr",
        parse_as: str = "raw",
    ) -> None:
        self.steps.append(
            {
                "type": "ocr",
                "nx": float(nx),
                "ny": float(ny),
                "nw": float(nw),
                "nh": float(nh),
                "variable": str(variable or "ocr"),
                "parse_as": str(parse_as or "raw"),
                "ocr_kind": "text",
                "color_hex": "",
                "needs_review": True,
                "description": "Inline OCR region (Atom Create — review parse_as).",
            }
        )
        self.selected_index = len(self.steps) - 1

    def remove_selected(self) -> int | None:
        if not self.steps:
            return None
        i = max(0, min(len(self.steps) - 1, self.selected_index))
        self.steps.pop(i)
        if not self.steps:
            self.selected_index = 0
            return None
        self.selected_index = min(i, len(self.steps) - 1)
        return self.selected_index

    def set_fire_mode(self, index: int, mode: str) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) not in {"click", "key"}:
            return
        kind = str(mode or "single").strip().lower()
        step["mode"] = "spam" if kind == "spam" else "single"
        if step["mode"] == "spam":
            ensure_spam_defaults(step)

    def toggle_fire_mode(self, index: int) -> str:
        if index < 0 or index >= len(self.steps):
            return "single"
        step = self.steps[index]
        if str(step.get("type")) not in {"click", "key"}:
            return "single"
        nxt = "single" if str(step.get("mode") or "single") == "spam" else "spam"
        self.set_fire_mode(index, nxt)
        return nxt

    def toggle_spam_by(self, index: int) -> str:
        if index < 0 or index >= len(self.steps):
            return "clicks"
        step = self.steps[index]
        if str(step.get("type")) not in {"click", "key"}:
            return "clicks"
        ensure_spam_defaults(step)
        nxt = "timed" if str(step.get("spam_by") or "clicks") == "clicks" else "clicks"
        step["spam_by"] = nxt
        step["mode"] = "spam"
        return nxt

    def set_click_amount(self, index: int, amount: int) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) not in {"click", "key"}:
            return
        ensure_spam_defaults(step)
        step["click_amount"] = max(1, int(amount))
        step["mode"] = "spam"
        step["spam_by"] = "clicks"

    def set_spam_duration_ms(self, index: int, duration_ms: int) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) not in {"click", "key"}:
            return
        ensure_spam_defaults(step)
        step["duration_ms"] = max(10, int(duration_ms))
        step["mode"] = "spam"
        step["spam_by"] = "timed"

    def set_spam_interval_ms(self, index: int, interval_ms: int) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) not in {"click", "key"}:
            return
        ensure_spam_defaults(step)
        step["interval_ms"] = max(10, int(interval_ms))
        step["mode"] = "spam"

    def snap_timed_spam_fields(self) -> list[int]:
        """On leaving Edit: snap timed spam durations so the last click is exact."""

        changed: list[int] = []
        for i, step in enumerate(self.steps):
            if str(step.get("type")) not in {"click", "key"}:
                continue
            if str(step.get("mode") or "single") != "spam":
                continue
            if str(step.get("spam_by") or "clicks") != "timed":
                continue
            ensure_spam_defaults(step)
            before = int(step.get("duration_ms") or 10)
            after = snap_spam_duration_ms(before, int(step.get("interval_ms") or 10))
            if after != before:
                step["duration_ms"] = after
                changed.append(i)
        return changed

    def set_drag_speed(self, index: int, speed: str) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "drag":
            return
        token = str(speed or "medium").strip().lower()
        if token not in {"slow", "medium", "fast"}:
            token = "medium"
        step["speed"] = token

    def set_drag_pause_end(self, index: int, *, enabled: bool, pause_ms: int | None = None) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "drag":
            return
        step["pause_end"] = bool(enabled)
        if pause_ms is not None:
            step["pause_ms"] = max(0, int(pause_ms))

    def set_ocr_kind(self, index: int, kind: str) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "ocr":
            return
        token = str(kind or "text").strip().lower()
        if token not in {"text", "color", "shape"}:
            token = "text"
        step["ocr_kind"] = token
        step["needs_review"] = True

    def set_ocr_color(self, index: int, color_hex: str) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "ocr":
            return
        raw = str(color_hex or "").strip()
        if raw and not raw.startswith("#"):
            raw = f"#{raw}"
        step["color_hex"] = raw
        step["ocr_kind"] = "color"
        step["needs_review"] = True

    def set_click_norm(self, index: int, *, nx: float, ny: float) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "click":
            return
        step["nx"] = float(max(0.0, min(1.0, nx)))
        step["ny"] = float(max(0.0, min(1.0, ny)))

    def set_drag_norm(
        self,
        index: int,
        *,
        which: str,
        nx: float,
        ny: float,
    ) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "drag":
            return
        tip = str(which or "start").lower()
        nx_c = float(max(0.0, min(1.0, nx)))
        ny_c = float(max(0.0, min(1.0, ny)))
        if tip in ("end", "1", "b"):
            step["nx1"] = nx_c
            step["ny1"] = ny_c
        else:
            step["nx0"] = nx_c
            step["ny0"] = ny_c

    def set_ocr_norm(
        self,
        index: int,
        *,
        nx: float | None = None,
        ny: float | None = None,
        nw: float | None = None,
        nh: float | None = None,
    ) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "ocr":
            return
        if nx is not None:
            step["nx"] = float(max(0.0, min(1.0, nx)))
        if ny is not None:
            step["ny"] = float(max(0.0, min(1.0, ny)))
        if nw is not None:
            step["nw"] = float(max(0.02, min(1.0, nw)))
        if nh is not None:
            step["nh"] = float(max(0.02, min(1.0, nh)))
        # Keep ROI inside unit square.
        nx_v = float(step.get("nx", 0.0))
        ny_v = float(step.get("ny", 0.0))
        nw_v = float(step.get("nw", 0.1))
        nh_v = float(step.get("nh", 0.1))
        if nx_v + nw_v > 1.0:
            step["nx"] = max(0.0, 1.0 - nw_v)
        if ny_v + nh_v > 1.0:
            step["ny"] = max(0.0, 1.0 - nh_v)

    def set_key(self, index: int, key: str) -> None:
        if index < 0 or index >= len(self.steps):
            return
        step = self.steps[index]
        if str(step.get("type")) != "key":
            return
        token = str(key or "").strip()
        if not token:
            return
        step["key"] = token
        step["pending"] = False
        step["description"] = f"Send key {token!r} (Atom Create)."

    def select_delta(self, delta: int) -> int:
        if not self.steps:
            self.selected_index = 0
            return 0
        self.selected_index = (self.selected_index + int(delta)) % len(self.steps)
        return self.selected_index

    def move_selected(self, delta: int) -> int:
        """Reorder selected step by delta (−1 up / +1 down). Returns new index."""

        if not self.steps:
            return 0
        i = max(0, min(len(self.steps) - 1, self.selected_index))
        j = i + int(delta)
        if j < 0 or j >= len(self.steps):
            self.selected_index = i
            return i
        self.steps[i], self.steps[j] = self.steps[j], self.steps[i]
        self.selected_index = j
        return j

    def clear(self) -> None:
        self.steps.clear()
        self.event_id = ""
        self.title = ""
        self.selected_index = 0
        self.kind = "automation"
        self.phases.clear()
        self.active_phase = ""
        self.home_phase = ""
        self.active_group = ""
        self.active_group_type = "overlay_menu"


def ensure_spam_defaults(step: dict[str, Any]) -> None:
    step.setdefault("spam_by", "clicks")
    step.setdefault("click_amount", 5)
    step.setdefault("duration_ms", 1000)
    step.setdefault("interval_ms", 50)
    step["click_amount"] = max(1, int(step.get("click_amount") or 5))
    step["duration_ms"] = max(10, int(step.get("duration_ms") or 1000))
    step["interval_ms"] = max(10, int(step.get("interval_ms") or 50))


def spam_click_count(*, duration_ms: int, interval_ms: int) -> int:
    """Clicks at 0, I, 2I, … while t <= duration. Always at least one."""

    interval_ms = max(10, int(interval_ms))
    duration_ms = max(10, int(duration_ms))
    return 1 + (duration_ms // interval_ms)


def snap_spam_duration_ms(duration_ms: int, interval_ms: int) -> int:
    """Make duration land exactly on the last click — no orphan leftover / phantom click."""

    interval_ms = max(10, int(interval_ms))
    duration_ms = max(10, int(duration_ms))
    n = spam_click_count(duration_ms=duration_ms, interval_ms=interval_ms)
    if n <= 1:
        return duration_ms
    return max(10, (n - 1) * interval_ms)


def step_label(step: dict[str, Any]) -> str:
    """Compact primary line for the queue (details go under via step_detail_lines)."""

    role = str(step.get("role") or "").strip()
    if role == "enter_key":
        return f"enter→{step.get('phase') or '?'}"
    if role == "exit_key":
        return f"exit←{step.get('phase') or '?'}"
    if role == "scroll_def":
        return f"scroll:{step.get('scroll_id') or step.get('label') or '?'}"
    if role == "target":
        kind = str(step.get("target_kind") or "action")
        return f"{kind}:{step.get('label') or step.get('target_id') or '?'}"
    if role == "scroll_region":
        return f"region:{step.get('region_id') or '?'}"
    if role == "phase_sense":
        return f"sense:{step.get('phase') or '?'}"
    kind = str(step.get("type") or "").strip().lower()
    if kind == "click":
        mode = str(step.get("mode") or "single")
        return "click spam" if mode == "spam" else "click"
    if kind == "drag":
        return "drag"
    if kind == "key":
        mode = str(step.get("mode") or "single")
        base = f"key:{step.get('key') or '?'}"
        return f"{base} spam" if mode == "spam" else base
    if kind == "ocr":
        ocr_kind = str(step.get("ocr_kind") or "text")
        return f"ocr:{ocr_kind}"
    if kind == "lco":
        return f"lco:{step.get('action') or '?'}"
    return kind or "?"


def _spam_detail_lines(step: dict[str, Any]) -> list[str]:
    mode = str(step.get("mode") or "single")
    lines = [f"→ mode {mode}"]
    if mode != "spam":
        return lines
    ensure_spam_defaults(step)
    spam_by = str(step.get("spam_by") or "clicks")
    lines.append(f"→ spam {spam_by}")
    if spam_by == "timed":
        lines.append(f"→ duration {int(step.get('duration_ms') or 10)}ms")
    else:
        lines.append(f"→ clicks {int(step.get('click_amount') or 1)}")
    lines.append(f"→ interval {int(step.get('interval_ms') or 10)}ms")
    return lines


def step_detail_lines(step: dict[str, Any]) -> list[str]:
    """Indented detail rows under a queue item (shown when D descriptions are on)."""

    kind = str(step.get("type") or "").strip().lower()
    lines: list[str] = []
    role = str(step.get("role") or "").strip()
    if role:
        lines.append(f"→ role {role}")
        if step.get("phase"):
            lines.append(f"→ phase {step.get('phase')}")
        if role == "target" and step.get("scrolls"):
            lines.append(f"→ scrolls {', '.join(str(s) for s in step.get('scrolls') or [])}")
        if role == "scroll_def" and step.get("scroll_id"):
            lines.append(f"→ id {step.get('scroll_id')}")
    if kind == "click":
        nx = float(step.get("nx", 0.5))
        ny = float(step.get("ny", 0.5))
        lines.append(f"→ position ({nx:.2f}, {ny:.2f})")
        lines.extend(_spam_detail_lines(step))
    elif kind == "drag":
        nx0 = float(step.get("nx0", 0.4))
        ny0 = float(step.get("ny0", 0.5))
        nx1 = float(step.get("nx1", 0.6))
        ny1 = float(step.get("ny1", 0.5))
        speed = str(step.get("speed") or "medium")
        pause = bool(step.get("pause_end"))
        pause_ms = int(step.get("pause_ms") or 0)
        lines.append(f"→ start ({nx0:.2f}, {ny0:.2f})")
        lines.append(f"→ end ({nx1:.2f}, {ny1:.2f})")
        lines.append(f"→ speed {speed}")
        lines.append(f"→ pause end {'yes ' + str(pause_ms) + 'ms' if pause else 'no'}")
    elif kind == "key":
        pending = bool(step.get("pending"))
        if pending:
            lines.append("→ waiting for key press")
        lines.extend(_spam_detail_lines(step))
    elif kind == "ocr":
        nx = float(step.get("nx", 0.35))
        ny = float(step.get("ny", 0.35))
        nw = float(step.get("nw", 0.3))
        nh = float(step.get("nh", 0.12))
        ocr_kind = str(step.get("ocr_kind") or "text")
        lines.append(f"→ region ({nx:.2f}, {ny:.2f}) {nw:.2f}×{nh:.2f}")
        lines.append(f"→ kind {ocr_kind}")
        if ocr_kind == "color" and step.get("color_hex"):
            lines.append(f"→ color {step.get('color_hex')}")
        if step.get("needs_review"):
            lines.append("→ needs review")
    elif kind == "lco":
        lines.append(f"→ action {step.get('action') or '?'}")
    return lines


def atom_create_prompt(*, phase: AtomCreatePhase | str, activate_key: str = "`") -> str:
    key = (activate_key or "`").strip() or "`"
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.KIND:
        return (
            "Atom Create — choose kind\n"
            "1 Automation · 2 Phase map\n"
            f"Esc = back to Atom Lab · {key} = pause Deck"
        )
    if kind is AtomCreatePhase.EDIT:
        return (
            "Atom Edit — W/S select · R/F reorder · Esc → Create\n"
            "Selected step highlights in the queue and on-screen glyphs\n"
            f"{key} = pause Flight Deck (keeps Create)"
        )
    if kind is AtomCreatePhase.PLAYBOOK:
        return (
            "Playbook (Tower) — B Buys · T Tabs · S Scroll · U Utility\n"
            "Same Flight Deck accordion; Esc returns to Create\n"
            f"{key} = pause Flight Deck (keeps Create)"
        )
    if kind is AtomCreatePhase.PHASE_MAP:
        from idle_lab.shell.atom_phase_map import phase_map_prompt

        return phase_map_prompt(activate_key=key)
    return (
        "Atom Create — B Basic Gesture · P Playbook · E Edit\n"
        "B expands 1–4 · P rewrites menu · Atom queue is the script\n"
        f"Esc = save → Atom Lab · {key} = pause Deck (keeps Create)"
    )


def atom_create_legend(*, phase: AtomCreatePhase | str) -> str:
    kind = phase if isinstance(phase, AtomCreatePhase) else AtomCreatePhase(str(phase))
    if kind is AtomCreatePhase.KIND:
        return "ATOM KIND · 1 AUTO · 2 PHASE MAP"
    if kind is AtomCreatePhase.EDIT:
        return "ATOM EDIT · W/S R/F · ESC = CREATE"
    if kind is AtomCreatePhase.PLAYBOOK:
        return "PLAYBOOK · ESC = CREATE"
    if kind is AtomCreatePhase.PHASE_MAP:
        from idle_lab.shell.atom_phase_map import phase_map_legend

        return phase_map_legend()
    return "ATOM CREATE · B GESTURE · P PLAYBOOK · E EDIT"


def build_atom_create_keymap(*, step_count: int = 0) -> FlightDeckKeymap:
    """Create root — Flight Deck accordion: B expands; P/E are leaves that change mode."""

    n = max(0, int(step_count))
    suffix = f" · {n} step(s)" if n else ""

    def leaf(key: str, label: str, action: dict[str, Any], *, description: str = "") -> KeymapNode:
        return KeymapNode(key=key, label=label, description=description, action=action)

    roots = [
        KeymapNode(
            key="B",
            label=f"Basic Gesture{suffix}",
            description="Ordinary human acts: click, drag, key, OCR.",
            children=[
                leaf(
                    "1",
                    "Click",
                    {"type": "atom_add_click"},
                    description="Numbered circle — drag to the target.",
                ),
                leaf(
                    "2",
                    "Drag",
                    {"type": "atom_add_drag"},
                    description="Start + end handles — drag each into place.",
                ),
                leaf(
                    "3",
                    "Key",
                    {"type": "atom_add_key"},
                    description="Next physical key becomes the step (Esc cancels).",
                ),
                leaf(
                    "4",
                    "OCR",
                    {"type": "atom_add_ocr"},
                    description="ROI rectangle — move body / SE grip resize.",
                ),
            ],
        ),
        leaf(
            "P",
            "Playbook (Tower)",
            {"type": "atom_playbook_enter"},
            description="Rewrites the Deck menu to Tower actuations. Esc returns.",
        ),
        leaf(
            "E",
            "Edit",
            {"type": "atom_edit_enter"},
            description="Select / reorder the queue. Esc returns to Create.",
        ),
    ]
    return FlightDeckKeymap(version=1, roots=roots)


def build_atom_playbook_keymap(*, step_count: int = 0) -> FlightDeckKeymap:
    """Rewritten Create menu — Tower playbook only (Esc peels back to Create root)."""

    n = max(0, int(step_count))
    suffix = f" · {n} step(s)" if n else ""

    def leaf(key: str, label: str, action: dict[str, Any], *, description: str = "") -> KeymapNode:
        return KeymapNode(key=key, label=label, description=description, action=action)

    return FlightDeckKeymap(
        version=1,
        roots=[
            KeymapNode(
                key="B",
                label=f"Buys{suffix}",
                description="Buy-slot actuations.",
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
                description="Workshop tab actuations.",
                children=[
                    leaf("1", "Attack", {"type": "atom_add_lco", "action": "tab_attack"}),
                    leaf("2", "Defense", {"type": "atom_add_lco", "action": "tab_defense"}),
                    leaf("3", "Utility", {"type": "atom_add_lco", "action": "tab_utility"}),
                ],
            ),
            KeymapNode(
                key="S",
                label="Scroll",
                description="Scroll / fling actuations.",
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
        ],
    )


def build_atom_edit_keymap(
    *,
    step_count: int = 0,
    selected_index: int = 0,
    selected_step: dict[str, Any] | None = None,
) -> FlightDeckKeymap:
    """Edit accordion — nav/reorder/remove + type-specific leaves for the selection."""

    n = max(0, int(step_count))
    sel = max(0, int(selected_index) + 1) if n else 0
    suffix = f" · {sel}/{n}" if n else " · empty"
    step = selected_step or {}
    kind = str(step.get("type") or "").strip().lower()

    def leaf(key: str, label: str, action: dict[str, Any], *, description: str = "") -> KeymapNode:
        return KeymapNode(key=key, label=label, description=description, action=action)

    roots: list[KeymapNode] = [
        leaf("W", f"Previous{suffix}", {"type": "atom_edit_prev"}, description="Select previous step."),
        leaf("S", "Next", {"type": "atom_edit_next"}, description="Select next step."),
        leaf("R", "Move up", {"type": "atom_edit_move_up"}, description="Reorder selected step earlier."),
        leaf("F", "Move down", {"type": "atom_edit_move_down"}, description="Reorder selected step later."),
        leaf("0", "Remove", {"type": "atom_edit_remove"}, description="Delete the selected step."),
    ]
    if kind in {"click", "key"}:
        mode = str(step.get("mode") or "single")
        roots.append(
            leaf(
                "1",
                f"Mode: {mode.capitalize()}",
                {"type": "atom_edit_toggle_mode"},
                description="Press to toggle Single ↔ Spam.",
            )
        )
        next_digit = 2
        if mode == "spam":
            ensure_spam_defaults(step)
            spam_by = str(step.get("spam_by") or "clicks")
            spam_label = "Clicks" if spam_by == "clicks" else "Timed"
            roots.append(
                leaf(
                    str(next_digit),
                    f"Spam: {spam_label}",
                    {"type": "atom_edit_toggle_spam_by"},
                    description="Press to toggle Clicks ↔ Timed.",
                )
            )
            next_digit += 1
            if spam_by == "clicks":
                roots.append(
                    leaf(
                        str(next_digit),
                        f"Click Amount: {int(step.get('click_amount') or 1)}",
                        {"type": "atom_edit_ask_click_amount"},
                        description="Press, then type how many clicks (min 1).",
                    )
                )
            else:
                roots.append(
                    leaf(
                        str(next_digit),
                        f"Duration: {int(step.get('duration_ms') or 10)}ms",
                        {"type": "atom_edit_ask_duration"},
                        description="Press, then type duration ms (min 10).",
                    )
                )
            next_digit += 1
            roots.append(
                leaf(
                    str(next_digit),
                    f"Interval: {int(step.get('interval_ms') or 10)}ms",
                    {"type": "atom_edit_ask_interval"},
                    description="Press, then type interval ms (min 10).",
                )
            )
            next_digit += 1
        if kind == "key":
            roots.append(
                leaf(
                    str(next_digit),
                    "Recapture key",
                    {"type": "atom_edit_recapture_key"},
                    description="Press a new key for this step.",
                )
            )
    if kind == "drag":
        speed = str(step.get("speed") or "medium")
        pause = bool(step.get("pause_end"))
        roots.extend(
            [
                leaf(
                    "1",
                    f"Speed: {speed.capitalize()}",
                    {"type": "atom_edit_drag_cycle_speed"},
                    description="Press to cycle Slow → Medium → Fast.",
                ),
                leaf(
                    "2",
                    f"Pause end: {'On' if pause else 'Off'}",
                    {"type": "atom_edit_drag_toggle_pause"},
                    description="Press to toggle hold-before-release.",
                ),
            ]
        )
    if kind == "ocr":
        ocr_kind = str(step.get("ocr_kind") or "text")
        color = str(step.get("color_hex") or "")
        roots.extend(
            [
                leaf(
                    "1",
                    f"Kind: {ocr_kind.capitalize()}",
                    {"type": "atom_edit_ocr_cycle_kind"},
                    description="Press to cycle Text → Color → Shape.",
                ),
                leaf(
                    "2",
                    f"Color: {color or '(none)'}",
                    {"type": "atom_edit_ocr_color"},
                    description="Press, then type #RRGGBB.",
                ),
            ]
        )
    roots.append(
        leaf("E", "Back to Create", {"type": "atom_edit_exit"}, description="Leave edit; stay in Atom Create.")
    )
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
        "kind": "automation",
        "description": "Authored via Atom Create (Molecule Lab).",
        "notes": "enabled:false by default — Run selected once from Molecule Lab Atom tab.",
        "actions": list(steps),
    }


def save_atom_draft(events_dir: Path, draft: AtomDraft) -> Path:
    if not draft.event_id.strip():
        raise ValueError("needs persist path — set event id before save")
    if not draft.steps:
        raise ValueError("needs at least one step before save")
    if str(draft.kind or "automation") == "phase_map":
        from idle_lab.shell.atom_phase_map import save_phase_map_draft

        path, _expanded = save_phase_map_draft(events_dir, draft, expand_targets=True)
        return path
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
