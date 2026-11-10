"""Molecule Lab draft model — context-gated palette, phases, step conditions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

StepKind = Literal["ensure_tab", "seek_and_buy", "molecule_ref", "event_ref"]
MoleculeKind = Literal["buy", "nav", "composite", "phase"]
PhaseId = Literal["beginning", "midgame", "endgame", "unfiled"]
ConditionOp = Literal["gte", "lte", "gt", "lt", "eq", "between", "nonempty"]
GatePolarity = Literal["perform", "skip"]

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
_CONDITION_OPS: frozenset[str] = frozenset({"gte", "lte", "gt", "lt", "eq", "between", "nonempty"})
_STATS_FIELDS: tuple[str, ...] = ("wave", "cash", "coins", "diamonds")


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


def _parse_op(raw: Any) -> ConditionOp:
    op = str(raw or "gte")
    if op not in _CONDITION_OPS:
        return "gte"
    return op  # type: ignore[return-value]


def _parse_num(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _looks_like_stats(token: str) -> bool:
    text = (token or "").lower()
    return "stat" in text


def outputs_for_step(step: DraftStep) -> list[str]:
    """Result fields a previous step can expose for condition authoring."""

    fields: list[str] = ["completed"]
    if step.kind == "ensure_tab":
        fields.append("tab_ready")
    elif step.kind == "seek_and_buy":
        fields.extend(["bought", "skipped_maxed", "skipped_unaffordable"])
    elif step.kind == "event_ref":
        event_id = step.event_id or step.label or ""
        if _looks_like_stats(event_id):
            fields.extend(_STATS_FIELDS)
    elif step.kind == "molecule_ref":
        mol_id = step.molecule_id or step.label or ""
        if _looks_like_stats(mol_id):
            fields.extend(_STATS_FIELDS)
    # Preserve order, drop dupes.
    seen: set[str] = set()
    ordered: list[str] = []
    for name in fields:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


@dataclass
class ConditionLeaf:
    """One predicate tied to a previous step's output field."""

    source_step: int
    field: str = "completed"
    op: ConditionOp = "gte"
    value: float | None = None
    value_hi: float | None = None

    def summary(self) -> str:
        src = f"step {self.source_step + 1}.{self.field}"
        if self.op == "nonempty":
            return f"{src} set"
        if self.op == "between" and self.value is not None and self.value_hi is not None:
            return f"{self.value:g} ≤ {src} ≤ {self.value_hi:g}"
        if self.op == "gte" and self.value is not None:
            return f"{src} ≥ {self.value:g}"
        if self.op == "lte" and self.value is not None:
            return f"{src} ≤ {self.value:g}"
        if self.op == "gt" and self.value is not None:
            return f"{src} > {self.value:g}"
        if self.op == "lt" and self.value is not None:
            return f"{src} < {self.value:g}"
        if self.op == "eq" and self.value is not None:
            return f"{src} = {self.value:g}"
        return f"{src} {self.op}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_step": self.source_step,
            "field": self.field,
            "op": self.op,
            "value": self.value,
            "value_hi": self.value_hi,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConditionLeaf | None:
        if not isinstance(data, dict) or "any" in data:
            return None
        if "source_step" not in data and "field" not in data and "variable" not in data:
            return None
        source = data.get("source_step")
        if source is None:
            return None
        try:
            source_step = int(source)
        except (TypeError, ValueError):
            return None
        field = str(data.get("field") or data.get("variable") or "completed")
        return cls(
            source_step=source_step,
            field=field,
            op=_parse_op(data.get("op")),
            value=_parse_num(data.get("value")),
            value_hi=_parse_num(data.get("value_hi")),
        )


@dataclass
class ConditionAny:
    """OR group of leaves — nested under root ``all``."""

    leaves: list[ConditionLeaf] = field(default_factory=list)

    def summary(self) -> str:
        if not self.leaves:
            return "(empty OR)"
        return "(" + " OR ".join(leaf.summary() for leaf in self.leaves) + ")"

    def to_dict(self) -> dict[str, Any]:
        return {"any": [leaf.to_dict() for leaf in self.leaves]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConditionAny | None:
        if not isinstance(data, dict) or "any" not in data:
            return None
        raw = data.get("any")
        if not isinstance(raw, list):
            return None
        leaves = [leaf for item in raw if isinstance(item, dict) for leaf in [ConditionLeaf.from_dict(item)] if leaf]
        return cls(leaves=leaves)


ConditionClause = ConditionLeaf | ConditionAny


@dataclass
class StepCondition:
    """Gate a draft step: root AND (`all`) with optional nested OR groups.

    Example: perform this buy when ``step1.wave ≥ 150`` AND ``(step1.wave < 400 OR step2.completed)``.
    Runtime enforcement is still emerging — Lab stores and previews the intent.
    """

    when_true: GatePolarity = "perform"
    all: list[ConditionClause] = field(default_factory=list)
    note: str = ""

    def is_empty(self) -> bool:
        return not self.all

    def summary(self) -> str:
        if not self.all:
            return "ungated"
        parts = [clause.summary() for clause in self.all]
        body = " AND ".join(parts)
        if self.when_true == "skip":
            return f"when true skip · {body}"
        return body

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "when_true": self.when_true,
            "all": [clause.to_dict() for clause in self.all],
        }
        if self.note:
            payload["note"] = self.note
        return payload

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
        *,
        step_index: int | None = None,
    ) -> StepCondition | None:
        if not isinstance(data, dict):
            return None
        # v2: when_true / all present (even if all is empty → treat as no gate).
        if "all" in data or "when_true" in data:
            raw_all = data.get("all") if isinstance(data.get("all"), list) else []
            clauses: list[ConditionClause] = []
            for item in raw_all:
                if not isinstance(item, dict):
                    continue
                if "any" in item:
                    group = ConditionAny.from_dict(item)
                    if group is not None and group.leaves:
                        clauses.append(group)
                else:
                    leaf = ConditionLeaf.from_dict(item)
                    if leaf is not None:
                        clauses.append(leaf)
            if not clauses:
                return None
            when = str(data.get("when_true") or "perform")
            if when not in {"perform", "skip"}:
                when = "perform"
            gate = cls(when_true=when, note=str(data.get("note") or ""), all=clauses)  # type: ignore[arg-type]
            if step_index is not None:
                gate = gate.filtered_for_step(step_index)
            return None if gate is None or gate.is_empty() else gate

        # v1 flat: variable / op / after_step
        if "variable" not in data and "op" not in data:
            return None
        source = _resolve_v1_source(data.get("after_step"), step_index)
        if source is None:
            return None
        leaf = ConditionLeaf(
            source_step=source,
            field=str(data.get("variable") or "wave"),
            op=_parse_op(data.get("op")),
            value=_parse_num(data.get("value")),
            value_hi=_parse_num(data.get("value_hi")),
        )
        return cls(when_true="perform", all=[leaf], note=str(data.get("note") or ""))

    def filtered_for_step(self, step_index: int) -> StepCondition | None:
        """Drop clauses that reference a non-previous source."""

        kept: list[ConditionClause] = []
        for clause in self.all:
            if isinstance(clause, ConditionLeaf):
                if 0 <= clause.source_step < step_index:
                    kept.append(clause)
            else:
                leaves = [leaf for leaf in clause.leaves if 0 <= leaf.source_step < step_index]
                if len(leaves) >= 2:
                    kept.append(ConditionAny(leaves=leaves))
                elif len(leaves) == 1:
                    kept.append(leaves[0])
        if not kept:
            return None
        return StepCondition(when_true=self.when_true, all=kept, note=self.note)

    def remap_sources(self, mapping: dict[int, int | None], *, step_index: int) -> StepCondition | None:
        """Apply index remap after reorder/remove; drop leaves that lost their source."""

        def _map_leaf(leaf: ConditionLeaf) -> ConditionLeaf | None:
            new_src = mapping.get(leaf.source_step, leaf.source_step)
            if new_src is None or not (0 <= new_src < step_index):
                return None
            return ConditionLeaf(
                source_step=new_src,
                field=leaf.field,
                op=leaf.op,
                value=leaf.value,
                value_hi=leaf.value_hi,
            )

        kept: list[ConditionClause] = []
        for clause in self.all:
            if isinstance(clause, ConditionLeaf):
                mapped = _map_leaf(clause)
                if mapped is not None:
                    kept.append(mapped)
            else:
                leaves = [m for leaf in clause.leaves if (m := _map_leaf(leaf)) is not None]
                if len(leaves) >= 2:
                    kept.append(ConditionAny(leaves=leaves))
                elif len(leaves) == 1:
                    kept.append(leaves[0])
        if not kept:
            return None
        return StepCondition(when_true=self.when_true, all=kept, note=self.note)


def _resolve_v1_source(after_step: Any, step_index: int | None) -> int | None:
    if step_index is None or step_index <= 0:
        return None
    if after_step is None:
        return step_index - 1
    try:
        after = int(after_step)
    except (TypeError, ValueError):
        return step_index - 1
    if after == -1:
        return step_index - 1
    if 0 <= after < step_index:
        return after
    return None


@dataclass
class DraftStep:
    kind: StepKind
    label: str
    tab: str | None = None
    catalog_id: str | None = None
    catalog_index: int | None = None
    molecule_id: str | None = None
    event_id: str | None = None
    guards: SeekGuards | None = None
    condition: StepCondition | None = None
    detail: str = ""

    def display_label(self) -> str:
        prefix = {
            "ensure_tab": "TAB",
            "seek_and_buy": "BUY",
            "molecule_ref": "MOL",
            "event_ref": "ATOM",
        }.get(self.kind, self.kind)
        base = f"[{prefix}] {self.label}"
        if self.condition is not None and not self.condition.is_empty():
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
            "event_id": self.event_id,
            "detail": self.detail,
        }
        if self.guards is not None:
            payload["guards"] = self.guards.as_dict()
        if self.condition is not None and not self.condition.is_empty():
            payload["condition"] = self.condition.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, step_index: int | None = None) -> DraftStep:
        guards_raw = data.get("guards")
        guards = None
        if isinstance(guards_raw, dict):
            guards = SeekGuards(
                too_far_up=tuple(str(x) for x in (guards_raw.get("too_far_up") or [])),
                too_far_down=tuple(str(x) for x in (guards_raw.get("too_far_down") or [])),
            )
        cond_raw = data.get("condition") if isinstance(data.get("condition"), dict) else None
        return cls(
            kind=str(data.get("kind") or "seek_and_buy"),  # type: ignore[arg-type]
            label=str(data.get("label") or ""),
            tab=(str(data["tab"]) if data.get("tab") else None),
            catalog_id=(str(data["catalog_id"]) if data.get("catalog_id") else None),
            catalog_index=(int(data["catalog_index"]) if data.get("catalog_index") is not None else None),
            molecule_id=(str(data["molecule_id"]) if data.get("molecule_id") else None),
            event_id=(str(data["event_id"]) if data.get("event_id") else None),
            guards=guards,
            condition=StepCondition.from_dict(cond_raw, step_index=step_index),
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
            mapping: dict[int, int | None] = {}
            for old in range(len(self.steps)):
                if old == index:
                    mapping[old] = None
                elif old > index:
                    mapping[old] = old - 1
                else:
                    mapping[old] = old
            self.steps.pop(index)
            self._remap_conditions(mapping)
            self._infer_kind()

    def move_step(self, index: int, delta: int) -> int | None:
        dest = index + delta
        if index < 0 or index >= len(self.steps) or dest < 0 or dest >= len(self.steps):
            return None
        mapping: dict[int, int | None] = {i: i for i in range(len(self.steps))}
        mapping[index] = dest
        mapping[dest] = index
        self.steps[index], self.steps[dest] = self.steps[dest], self.steps[index]
        self._remap_conditions(mapping)
        return dest

    def clear_steps(self) -> None:
        self.steps.clear()
        self.requires_tab = None
        self.kind = "buy"

    def _infer_kind(self) -> None:
        if any(s.kind in {"molecule_ref", "event_ref"} for s in self.steps):
            if self.kind not in {"composite", "phase"}:
                self.kind = "composite"
        elif self.steps and all(s.kind in {"ensure_tab", "seek_and_buy"} for s in self.steps):
            if self.kind == "composite":
                self.kind = "buy"

    def _remap_conditions(self, mapping: dict[int, int | None]) -> None:
        for i, step in enumerate(self.steps):
            if step.condition is None:
                continue
            step.condition = step.condition.remap_sources(mapping, step_index=i)

    def _reindex_conditions(self) -> None:
        """Drop illegal previous-step references after structural edits."""

        for i, step in enumerate(self.steps):
            if step.condition is None:
                continue
            step.condition = step.condition.filtered_for_step(i)

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
        steps = [
            DraftStep.from_dict(item, step_index=i)
            for i, item in enumerate(steps_raw)
            if isinstance(item, dict)
        ]
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
    event_id: str | None = None
    guards: SeekGuards | None = None
    enabled: bool = True
    disabled_reason: str = ""


# Atoms that phase packs commonly nest (sensors / collectors).
_SENSOR_ATOMS: tuple[tuple[str, str, str], ...] = (
    (
        "stat_collect",
        "Stat collect",
        "OCR wave + currencies into runtime variables (sticky until next collect).",
    ),
)


def infer_phase_from_text(*parts: str) -> PhaseId:
    text = " ".join(p for p in parts if p).lower()
    if any(token in text for token in ("beginning", "early", "start phase", "openers")):
        return "beginning"
    if any(token in text for token in ("midgame", "mid-game", "mid game", "mid phase")):
        return "midgame"
    if any(token in text for token in ("endgame", "end-game", "end game", "late")):
        return "endgame"
    return "unfiled"


def _sensor_palette_items() -> list[PaletteItem]:
    return [
        PaletteItem(
            key=f"atom:{event_id}",
            kind="event_ref",
            label=title,
            group="Sensors / atoms",
            detail=detail,
            event_id=event_id,
        )
        for event_id, title, detail in _SENSOR_ATOMS
    ]


def _nest_library_items(
    library: list[dict[str, Any]],
    *,
    group: str,
    exclude_id: str | None = None,
    only_tab: str | None = None,
    exclude_tab: str | None = None,
) -> list[PaletteItem]:
    """Nestable saved molecules. Tab filters are optional — empty = all."""

    items: list[PaletteItem] = []
    for mol in library:
        mol_id = str(mol.get("id") or "").strip()
        if not mol_id or (exclude_id and mol_id == exclude_id):
            continue
        req = (mol.get("requires_tab") or "").strip().lower()
        if only_tab is not None and req and req != only_tab:
            continue
        if exclude_tab is not None and req == exclude_tab:
            continue
        tab_note = f" (authored for {req})" if req else ""
        items.append(
            PaletteItem(
                key=f"mol:{mol_id}",
                kind="molecule_ref",
                label=str(mol.get("title") or mol_id),
                group=group,
                detail=str(mol.get("description") or f"Nest this molecule{tab_note}."),
                tab=req or None,
                molecule_id=mol_id,
            )
        )
    return items


def build_palette(
    *,
    context: ComposerContext,
    tabs: dict[str, Any],
    library: list[dict[str, Any]] | None = None,
    exclude_molecule_id: str | None = None,
) -> list[PaletteItem]:
    """Palette for authoring.

    Empty context → open-tab gates + nest any saved molecule + sensor atoms.
    After a tab is selected → that tab's upgrades, same-tab saves, then nest
    other-tab molecules + sensors (so phase packs can mix Attack + Defense).
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
        items.extend(
            _nest_library_items(
                library,
                group="Nest molecule",
                exclude_id=exclude_molecule_id,
            )
        )
        items.extend(_sensor_palette_items())
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

    # Same-tab saves (+ molecules with no tab requirement).
    items.extend(
        _nest_library_items(
            library,
            group="Nest molecule (this tab)",
            exclude_id=exclude_molecule_id,
            only_tab=tab,
        )
    )
    # Cross-tab packs (e.g. Defense while authoring under Attack).
    cross = [
        item
        for item in _nest_library_items(
            library,
            group="Nest molecule (other tab)",
            exclude_id=exclude_molecule_id,
            exclude_tab=tab,
        )
        if item.tab and item.tab != tab
    ]
    items.extend(cross)
    items.extend(_sensor_palette_items())
    return items
