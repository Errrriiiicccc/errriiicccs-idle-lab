"""Molecule Lab draft model — context-gated palette, phases, step conditions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

StepKind = Literal["ensure_tab", "seek_and_buy", "molecule_ref"]
MoleculeKind = Literal["buy", "nav", "composite", "phase"]
PhaseId = Literal["beginning", "midgame", "endgame", "unfiled"]
ConditionOp = Literal["gte", "lte", "eq", "between", "nonempty"]

PHASE_ORDER: tuple[PhaseId, ...] = ("beginning", "midgame", "endgame", "unfiled")
PHASE_LABELS: dict[str, str] = {
    "beginning": "Beginning",
    "midgame": "Midgame",
    "endgame": "Endgame",
    "unfiled": "Unfiled",
}
KIND_LABELS: dict[str, str] = {
    "buy": "Buy",
    "nav": "Nav",
    "composite": "Composite",
    "phase": "Phase pack",
}


@dataclass(frozen=True)
class SeekGuards:
    """If these labels land on slot 1, we scrolled the wrong way."""

    too_far_up: tuple[str, ...] = ()
    too_far_down: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "too_far_up": list(self.too_far_up),
            "too_far_down": list(self.too_far_down),
        }


@dataclass
class StepCondition:
    """Gate a step on a variable (and optionally on a prior step having run).

    Example: run this buy only when ``wave >= 1000`` after the previous step.
    Runtime enforcement is still emerging — Lab stores and previews the intent.
    """

    variable: str = "wave"
    op: ConditionOp = "gte"
    value: float | None = None
    value_hi: float | None = None
    # None = independent; -1 = immediately previous step; >=0 = absolute index
    after_step: int | None = None
    note: str = ""

    def summary(self) -> str:
        var = self.variable or "?"
        if self.op == "nonempty":
            body = f"{var} set"
        elif self.op == "between" and self.value is not None and self.value_hi is not None:
            body = f"{self.value:g} ≤ {var} ≤ {self.value_hi:g}"
        elif self.op == "gte" and self.value is not None:
            body = f"{var} ≥ {self.value:g}"
        elif self.op == "lte" and self.value is not None:
            body = f"{var} ≤ {self.value:g}"
        elif self.op == "eq" and self.value is not None:
            body = f"{var} = {self.value:g}"
        else:
            body = f"{var} {self.op}"
        if self.after_step == -1:
            body = f"after prev · {body}"
        elif self.after_step is not None and self.after_step >= 0:
            body = f"after step {self.after_step + 1} · {body}"
        return body

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "op": self.op,
            "value": self.value,
            "value_hi": self.value_hi,
            "after_step": self.after_step,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> StepCondition | None:
        if not isinstance(data, dict):
            return None
        op = str(data.get("op") or "gte")
        if op not in {"gte", "lte", "eq", "between", "nonempty"}:
            op = "gte"
        after = data.get("after_step")
        after_step = int(after) if after is not None else None
        value = data.get("value")
        value_hi = data.get("value_hi")
        return cls(
            variable=str(data.get("variable") or "wave"),
            op=op,  # type: ignore[arg-type]
            value=float(value) if value is not None and value != "" else None,
            value_hi=float(value_hi) if value_hi is not None and value_hi != "" else None,
            after_step=after_step,
            note=str(data.get("note") or ""),
        )


@dataclass
class DraftStep:
    kind: StepKind
    label: str
    tab: str | None = None
    catalog_id: str | None = None
    catalog_index: int | None = None
    molecule_id: str | None = None
    guards: SeekGuards | None = None
    condition: StepCondition | None = None
    detail: str = ""

    def display_label(self) -> str:
        prefix = {
            "ensure_tab": "TAB",
            "seek_and_buy": "BUY",
            "molecule_ref": "MOL",
        }.get(self.kind, self.kind)
        base = f"[{prefix}] {self.label}"
        if self.condition is not None:
            return f"{base}  ·  if {self.condition.summary()}"
        return base

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "label": self.label,
            "tab": self.tab,
            "catalog_id": self.catalog_id,
            "catalog_index": self.catalog_index,
            "molecule_id": self.molecule_id,
            "detail": self.detail,
        }
        if self.guards is not None:
            payload["guards"] = self.guards.as_dict()
        if self.condition is not None:
            payload["condition"] = self.condition.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DraftStep:
        guards_raw = data.get("guards")
        guards = None
        if isinstance(guards_raw, dict):
            guards = SeekGuards(
                too_far_up=tuple(str(x) for x in (guards_raw.get("too_far_up") or [])),
                too_far_down=tuple(str(x) for x in (guards_raw.get("too_far_down") or [])),
            )
        return cls(
            kind=str(data.get("kind") or "seek_and_buy"),  # type: ignore[arg-type]
            label=str(data.get("label") or ""),
            tab=(str(data["tab"]) if data.get("tab") else None),
            catalog_id=(str(data["catalog_id"]) if data.get("catalog_id") else None),
            catalog_index=(int(data["catalog_index"]) if data.get("catalog_index") is not None else None),
            molecule_id=(str(data["molecule_id"]) if data.get("molecule_id") else None),
            guards=guards,
            condition=StepCondition.from_dict(data.get("condition") if isinstance(data.get("condition"), dict) else None),
            detail=str(data.get("detail") or ""),
        )


@dataclass
class ComposerContext:
    """Authoring context — gates which palette buttons are legal."""

    tab: str | None = None

    def enter_tab(self, tab: str) -> None:
        self.tab = tab.strip().lower() or None

    def clear(self) -> None:
        self.tab = None


@dataclass
class ComposerDraft:
    title: str = "Untitled molecule"
    steps: list[DraftStep] = field(default_factory=list)
    draft_id: str = field(default_factory=lambda: uuid4().hex[:10])
    requires_tab: str | None = None
    notes: str = ""
    phase: PhaseId = "unfiled"
    kind: MoleculeKind = "buy"
    collection_id: str | None = None

    def add_step(self, step: DraftStep) -> None:
        self.steps.append(step)
        if step.tab and self.requires_tab is None:
            self.requires_tab = step.tab
        self._infer_kind()

    def remove_at(self, index: int) -> None:
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
            self._reindex_conditions()
            self._infer_kind()

    def move_step(self, index: int, delta: int) -> int | None:
        dest = index + delta
        if index < 0 or index >= len(self.steps) or dest < 0 or dest >= len(self.steps):
            return None
        self.steps[index], self.steps[dest] = self.steps[dest], self.steps[index]
        self._reindex_conditions()
        return dest

    def clear_steps(self) -> None:
        self.steps.clear()
        self.requires_tab = None
        self.kind = "buy"

    def _infer_kind(self) -> None:
        if any(s.kind == "molecule_ref" for s in self.steps):
            if self.kind not in {"composite", "phase"}:
                self.kind = "composite"
        elif self.steps and all(s.kind in {"ensure_tab", "seek_and_buy"} for s in self.steps):
            if self.kind == "composite":
                self.kind = "buy"

    def _reindex_conditions(self) -> None:
        for step in self.steps:
            cond = step.condition
            if cond is None or cond.after_step is None or cond.after_step < 0:
                continue
            if cond.after_step >= len(self.steps):
                cond.after_step = -1

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "title": self.title,
            "requires_tab": self.requires_tab,
            "notes": self.notes,
            "phase": self.phase,
            "kind": self.kind,
            "collection_id": self.collection_id,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComposerDraft:
        steps_raw = data.get("steps") or []
        steps = [DraftStep.from_dict(item) for item in steps_raw if isinstance(item, dict)]
        phase = str(data.get("phase") or "unfiled")
        if phase not in PHASE_LABELS:
            phase = "unfiled"
        kind = str(data.get("kind") or "buy")
        if kind not in KIND_LABELS:
            kind = "buy"
        return cls(
            title=str(data.get("title") or "Untitled molecule"),
            steps=steps,
            draft_id=str(data.get("draft_id") or uuid4().hex[:10]),
            requires_tab=(str(data["requires_tab"]) if data.get("requires_tab") else None),
            notes=str(data.get("notes") or ""),
            phase=phase,  # type: ignore[arg-type]
            kind=kind,  # type: ignore[arg-type]
            collection_id=(str(data["collection_id"]) if data.get("collection_id") else None),
        )


@dataclass(frozen=True)
class PaletteItem:
    """One choosable entry in the context-gated palette."""

    key: str
    kind: StepKind
    label: str
    group: str
    detail: str = ""
    tab: str | None = None
    catalog_id: str | None = None
    catalog_index: int | None = None
    molecule_id: str | None = None
    guards: SeekGuards | None = None
    enabled: bool = True
    disabled_reason: str = ""


def infer_phase_from_text(*parts: str) -> PhaseId:
    text = " ".join(p for p in parts if p).lower()
    if any(token in text for token in ("beginning", "early", "start phase", "openers")):
        return "beginning"
    if any(token in text for token in ("midgame", "mid-game", "mid game", "mid phase")):
        return "midgame"
    if any(token in text for token in ("endgame", "end-game", "end game", "late")):
        return "endgame"
    return "unfiled"


def build_palette(
    *,
    context: ComposerContext,
    tabs: dict[str, Any],
    library: list[dict[str, Any]] | None = None,
) -> list[PaletteItem]:
    """Only show actions the operator could press in the current context.

    Empty context → tab gates only.
    After a tab is selected → that tab's upgrades + library molecules scoped to it
    (plus composites that declare no tab requirement).
    """

    items: list[PaletteItem] = []
    library = library or []

    if context.tab is None:
        for tab_id, caps in tabs.items():
            hotkey = getattr(caps, "hotkey", "") or ""
            label = getattr(caps, "label", tab_id.title())
            suffix = f" [{hotkey}]" if hotkey else ""
            items.append(
                PaletteItem(
                    key=f"tab:{tab_id}",
                    kind="ensure_tab",
                    label=f"{label}{suffix}",
                    group="Open tab",
                    detail="Enter this upgrade tab before buys on its list are available.",
                    tab=tab_id,
                )
            )
        # Composites / phase packs usable without a buy-tab context.
        for mol in library:
            kind = str(mol.get("kind") or "")
            req = (mol.get("requires_tab") or "").strip().lower()
            if req:
                continue
            if kind not in {"composite", "phase"} and not mol.get("children"):
                continue
            mol_id = str(mol.get("id") or "").strip()
            if not mol_id:
                continue
            items.append(
                PaletteItem(
                    key=f"mol:{mol_id}",
                    kind="molecule_ref",
                    label=str(mol.get("title") or mol_id),
                    group="Composite / phase molecules",
                    detail=str(mol.get("description") or "Nest this molecule."),
                    molecule_id=mol_id,
                )
            )
        return items

    tab = context.tab
    caps = tabs.get(tab)
    if caps is None:
        return items

    items.append(
        PaletteItem(
            key="ctx:clear_tab",
            kind="ensure_tab",
            label="← Leave tab context",
            group="Context",
            detail="Return to tab selection. Draft steps are kept.",
            tab=None,
        )
    )

    for entry in getattr(caps, "catalog", ()) or ():
        guards = caps.guards_for(entry) if hasattr(caps, "guards_for") else SeekGuards()
        page = "page-1" if entry.index < 6 else "seek"
        items.append(
            PaletteItem(
                key=f"buy:{entry.id}",
                kind="seek_and_buy",
                label=entry.label,
                group=f"{caps.label} upgrades",
                detail=(
                    f"{page}: find {entry.label} relative to the viewport, "
                    f"correct overshoot via neighbors, then buy. "
                    f"Skip if maxed/unaffordable (stub)."
                ),
                tab=tab,
                catalog_id=entry.id,
                catalog_index=entry.index,
                guards=guards,
            )
        )

    for mol in library:
        req = (mol.get("requires_tab") or "").strip().lower()
        mol_id = str(mol.get("id") or "").strip()
        if not mol_id:
            continue
        # Show tab-scoped buys + any composite that can nest here.
        if req and req != tab:
            continue
        items.append(
            PaletteItem(
                key=f"mol:{mol_id}",
                kind="molecule_ref",
                label=str(mol.get("title") or mol_id),
                group="Saved molecules",
                detail=str(mol.get("description") or "Reuse a previously composed molecule."),
                tab=req or tab,
                molecule_id=mol_id,
            )
        )
    return items
