"""Expand a composer draft into atom/molecule JSON on disk (files stay truth)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.composer.catalog import CapabilityCatalog, TabCapabilities
from idle_lab.composer.model import ComposerDraft, DraftStep, SeekGuards
from idle_lab.presets import slug


class ComposerExpandError(ValueError):
    """Draft cannot be expanded into valid automation files."""


@dataclass
class ExportResult:
    collection_id: str
    collection_path: Path
    event_paths: list[Path] = field(default_factory=list)
    library_path: Path | None = None
    draft_path: Path | None = None
    preview_lines: list[str] = field(default_factory=list)


def library_path(automations_root: Path) -> Path:
    return Path(automations_root) / "composer" / "library.json"


def drafts_dir(automations_root: Path) -> Path:
    return Path(automations_root) / "composer" / "drafts"


def load_library(automations_root: Path) -> list[dict[str, Any]]:
    path = library_path(automations_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    molecules = data.get("molecules") if isinstance(data, dict) else None
    if not isinstance(molecules, list):
        return []
    return [item for item in molecules if isinstance(item, dict)]


def _slug_id(prefix: str, title: str) -> str:
    body = slug(title).replace("-", "_")
    body = re.sub(r"_+", "_", body).strip("_") or "molecule"
    return f"{prefix}_{body}"


def _guard_note(guards: SeekGuards | None) -> str:
    if guards is None:
        return "No neighbor guards declared."
    up = ", ".join(guards.too_far_up) or "—"
    down = ", ".join(guards.too_far_down) or "—"
    return (
        f"Relative seek: if slot-1 shows [{up}] we overshot upward — scroll down. "
        f"If slot-1 shows [{down}] we overshot downward — scroll up. "
        f"Then buy the matching card. Skip when maxed/unaffordable (perception stub)."
    )


def _seek_buy_actions(step: DraftStep, caps: TabCapabilities | None) -> list[dict[str, Any]]:
    tab = (step.tab or (caps.tab if caps else "") or "attack").lower()
    lco_tab = caps.lco_action if caps else f"tab_{tab}"
    index = int(step.catalog_index) if step.catalog_index is not None else 0
    actions: list[dict[str, Any]] = [
        {
            "type": "lco",
            "action": lco_tab,
            "description": f"Ensure {tab.title()} tab (homes list).",
        }
    ]

    # Page-1: home + direct buy slot. Deeper: approximate row scroll, then column buy.
    if index < 6:
        slot = index + 1
        actions.append(
            {
                "type": "lco",
                "action": f"buy_{slot}",
                "description": f"Buy {step.label} (page-1 slot {slot}).",
            }
        )
        return actions

    rows = index // 2  # put target row at top after home
    column_left = True
    if caps is not None:
        entry = next((e for e in caps.catalog if e.index == index), None)
        if entry is not None and entry.column == "right":
            column_left = False
    slot = 1 if column_left else 2
    if rows > 0:
        actions.append(
            {
                "type": "scroll_list",
                "direction": "down",
                "rows": rows,
                "description": (
                    f"Approx scroll {rows} row(s) toward {step.label}. "
                    "Replace with OCR-relative seek when ready."
                ),
            }
        )
    actions.append(
        {
            "type": "log",
            "level": "info",
            "message": f"composer seek guards — {_guard_note(step.guards)}",
            "description": "Fail-guard policy (runtime OCR will enforce later).",
        }
    )
    actions.append(
        {
            "type": "lco",
            "action": f"buy_{slot}",
            "description": (
                f"Buy {step.label} at estimated top-row slot {slot}. "
                "Skip if maxed/unaffordable once buy visual states land."
            ),
        }
    )
    return actions


def _event_payload(event_id: str, title: str, description: str, notes: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": event_id,
        "title": title,
        "version": 1,
        "enabled": False,
        "priority": 50,
        "timing": {"type": "interval", "every_ms": 60000},
        "description": description,
        "notes": notes,
        "actions": actions,
    }


def _expand_step(
    step: DraftStep,
    catalog: CapabilityCatalog,
    *,
    molecule_slug: str,
    seq: int,
) -> tuple[str, dict[str, Any] | None, str]:
    """Return (child_id, optional new event dict, preview line)."""

    if step.kind == "ensure_tab":
        tab = (step.tab or "").lower()
        caps = catalog.tabs.get(tab)
        event_id = f"composer_{molecule_slug}_tab_{tab or seq}"
        actions = [
            {
                "type": "lco",
                "action": caps.lco_action if caps else f"tab_{tab}",
                "description": f"Open {caps.label if caps else tab} tab.",
            }
        ]
        payload = _event_payload(
            event_id,
            title=f"Ensure {caps.label if caps else tab.title()}",
            description=f"Composer atom: open {tab} upgrade tab.",
            notes="Generated by molecule composer.",
            actions=actions,
        )
        return event_id, payload, f"ensure tab → {tab}"

    if step.kind == "molecule_ref":
        mol_id = step.molecule_id or ""
        if not mol_id:
            raise ComposerExpandError("molecule_ref step missing molecule_id")
        return mol_id, None, f"reuse molecule → {mol_id}"

    if step.kind == "seek_and_buy":
        tab = (step.tab or "").lower()
        caps = catalog.tabs.get(tab)
        label_slug = slug(step.label).replace("-", "_")
        event_id = f"composer_{molecule_slug}_{label_slug}"
        actions = _seek_buy_actions(step, caps)
        notes = (
            f"Generated by molecule composer.\n{_guard_note(step.guards)}\n"
            f"catalog_id={step.catalog_id} index={step.catalog_index}"
        )
        payload = _event_payload(
            event_id,
            title=f"Seek+Buy {step.label}",
            description=(
                f"Composer atom: relative-seek {step.label} on {tab.title()} "
                "then buy (skip maxed/unaffordable when perception supports it)."
            ),
            notes=notes,
            actions=actions,
        )
        guard_bits = ""
        if step.guards and step.guards.too_far_down:
            guard_bits = f" (guard down: {', '.join(step.guards.too_far_down)})"
        return event_id, payload, f"seek+buy → {step.label}{guard_bits}"

    raise ComposerExpandError(f"unknown step kind: {step.kind}")


def preview_expansion(draft: ComposerDraft, catalog: CapabilityCatalog) -> list[str]:
    if not draft.steps:
        return ["(empty draft)"]
    molecule_slug = slug(draft.title).replace("-", "_") or "molecule"
    lines: list[str] = [f"Molecule: {draft.title}"]
    for i, step in enumerate(draft.steps, start=1):
        _child, _payload, line = _expand_step(step, catalog, molecule_slug=molecule_slug, seq=i)
        lines.append(f"  {i}. {line}")
    return lines


def expand_and_write(
    draft: ComposerDraft,
    *,
    automations_root: Path,
    catalog: CapabilityCatalog,
) -> ExportResult:
    if not draft.steps:
        raise ComposerExpandError("Add at least one step before saving.")
    title = draft.title.strip() or "Untitled molecule"
    molecule_slug = slug(title).replace("-", "_") or "molecule"
    collection_id = _slug_id("mol", title)

    root = Path(automations_root)
    events_dir = root / "events"
    collections_dir = root / "collections"
    events_dir.mkdir(parents=True, exist_ok=True)
    collections_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir(root).mkdir(parents=True, exist_ok=True)
    (root / "composer").mkdir(parents=True, exist_ok=True)

    children: list[str] = []
    event_paths: list[Path] = []
    preview: list[str] = [f"Molecule: {title}"]

    for i, step in enumerate(draft.steps, start=1):
        child_id, payload, line = _expand_step(step, catalog, molecule_slug=molecule_slug, seq=i)
        children.append(child_id)
        preview.append(f"  {i}. {line}")
        if payload is not None:
            path = events_dir / f"{child_id}.json"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            event_paths.append(path)

    requires = draft.requires_tab or next((s.tab for s in draft.steps if s.tab), None)
    collection = {
        "id": collection_id,
        "title": title,
        "version": 1,
        "description": (
            f"Composer molecule"
            + (f" (requires {requires} tab context)." if requires else ".")
        ),
        "children": children,
        "branch_variable": "phase",
        "branches": {},
        "loop": False,
        "stop_when": None,
        "run": "once",
        "notes": (
            "Authored via molecule composer. Files are source of truth — edit JSON or re-export. "
            "Phase/stat branching is stubbed for a later pass."
        ),
    }
    collection_path = collections_dir / f"{collection_id}.json"
    collection_path.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")

    draft_path = drafts_dir(root) / f"{collection_id}.json"
    draft_payload = draft.to_dict()
    draft_payload["collection_id"] = collection_id
    draft_payload["title"] = title
    draft_payload["requires_tab"] = requires
    draft_path.write_text(json.dumps(draft_payload, indent=2) + "\n", encoding="utf-8")

    lib_path = library_path(root)
    molecules = load_library(root)
    entry = {
        "id": collection_id,
        "title": title,
        "requires_tab": requires,
        "description": collection["description"],
        "children": children,
    }
    molecules = [m for m in molecules if str(m.get("id")) != collection_id]
    molecules.append(entry)
    lib_path.write_text(
        json.dumps({"version": 1, "molecules": molecules}, indent=2) + "\n",
        encoding="utf-8",
    )

    return ExportResult(
        collection_id=collection_id,
        collection_path=collection_path,
        event_paths=event_paths,
        library_path=lib_path,
        draft_path=draft_path,
        preview_lines=preview,
    )
