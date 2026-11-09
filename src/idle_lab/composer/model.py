"""Composer draft + context-gated palette (no OCR required)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

StepKind = Literal["ensure_tab", "seek_and_buy", "molecule_ref"]


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
class DraftStep:
    kind: StepKind
    label: str
    tab: str | None = None
    catalog_id: str | None = None
    catalog_index: int | None = None
    molecule_id: str | None = None
    guards: SeekGuards | None = None
    detail: str = ""

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

    def add_step(self, step: DraftStep) -> None:
        self.steps.append(step)
        if step.tab and self.requires_tab is None:
            self.requires_tab = step.tab

    def remove_at(self, index: int) -> None:
        if 0 <= index < len(self.steps):
            self.steps.pop(index)

    def clear_steps(self) -> None:
        self.steps.clear()
        self.requires_tab = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "title": self.title,
            "requires_tab": self.requires_tab,
            "notes": self.notes,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComposerDraft:
        steps_raw = data.get("steps") or []
        steps = [DraftStep.from_dict(item) for item in steps_raw if isinstance(item, dict)]
        return cls(
            title=str(data.get("title") or "Untitled molecule"),
            steps=steps,
            draft_id=str(data.get("draft_id") or uuid4().hex[:10]),
            requires_tab=(str(data["requires_tab"]) if data.get("requires_tab") else None),
            notes=str(data.get("notes") or ""),
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


def build_palette(
    *,
    context: ComposerContext,
    tabs: dict[str, Any],
    library: list[dict[str, Any]] | None = None,
) -> list[PaletteItem]:
    """Only show actions the operator could press in the current context.

    Empty context → tab gates only.
    After a tab is selected → that tab's upgrades + library molecules scoped to it.
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
        if req and req != tab:
            continue
        mol_id = str(mol.get("id") or "").strip()
        if not mol_id:
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
