"""Expand a Molecule Lab draft into atom/molecule JSON on disk (files stay truth)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.composer.catalog import CapabilityCatalog, TabCapabilities
from idle_lab.composer.model import (
    ComposerDraft,
    DraftStep,
    SeekGuards,
    StepCondition,
    infer_phase_from_text,
)
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
    """Composer library plus on-disk collections (so Lab can browse everything)."""

    path = library_path(automations_root)
    molecules: list[dict[str, Any]] = []
    seen: set[str] = set()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        raw = data.get("molecules") if isinstance(data, dict) else None
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                mol_id = str(item.get("id") or "").strip()
                if not mol_id or mol_id in seen:
                    continue
                seen.add(mol_id)
                molecules.append(dict(item))

    collections_dir = Path(automations_root) / "collections"
    if collections_dir.exists():
        for file_path in sorted(collections_dir.glob("*.json")):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            mol_id = str(data.get("id") or "").strip()
            if not mol_id or mol_id in seen:
                continue
            seen.add(mol_id)
            phase = str(data.get("phase") or "") or infer_phase_from_text(
                mol_id, str(data.get("title") or ""), str(data.get("description") or "")
            )
            children = data.get("children") if isinstance(data.get("children"), list) else []
            kind = str(data.get("kind") or "")
            if not kind:
                kind = "composite" if any(True for _ in children) else "buy"
                # Heuristic: nested molecule ids often look like collections.
                if any(str(c).startswith("mol_") or str(c).endswith("_loop") for c in children):
                    kind = "composite"
                if "phase" in mol_id or "phase" in str(data.get("title") or "").lower():
                    kind = "phase"
            molecules.append(
                {
                    "id": mol_id,
                    "title": str(data.get("title") or mol_id),
                    "requires_tab": data.get("requires_tab"),
                    "description": str(data.get("description") or ""),
                    "children": [str(c) for c in children],
                    "phase": phase,
                    "kind": kind,
                    "source": "collections",
                }
            )
    return molecules


def load_draft(automations_root: Path, collection_id: str) -> ComposerDraft | None:
    path = drafts_dir(automations_root) / f"{collection_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    draft = ComposerDraft.from_dict(data)
    draft.collection_id = collection_id
    return draft


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


def _condition_note(cond: StepCondition | None) -> str:
    if cond is None or cond.is_empty():
        return ""
    return f"Condition: {cond.summary()}" + (f" — {cond.note}" if cond.note else "")


def _condition_actions(cond: StepCondition | None) -> list[dict[str, Any]]:
    """Emit a log gate today; headless/OCR can turn this into real decide later."""

    if cond is None or cond.is_empty():
        return []
    if cond.when_true == "skip":
        intent = f"Would skip this step when ({cond.summary()})."
    else:
        intent = f"Would perform this step only when ({cond.summary()})."
    return [
        {
            "type": "log",
            "level": "info",
            "message": f"molecule-lab gate — {_condition_note(cond)}",
            "description": (
                f"{intent} "
                "Runtime numeric compare + skip land with C5; authoring stores the intent."
            ),
        }
    ]


def _seek_buy_actions(step: DraftStep, caps: TabCapabilities | None) -> list[dict[str, Any]]:
    tab = (step.tab or (caps.tab if caps else "") or "attack").lower()
    lco_tab = caps.lco_action if caps else f"tab_{tab}"
    index = int(step.catalog_index) if step.catalog_index is not None else 0
    actions: list[dict[str, Any]] = list(_condition_actions(step.condition))
    actions.append(
        {
            "type": "lco",
            "action": lco_tab,
            "description": f"Ensure {tab.title()} tab (homes list).",
        }
    )

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

    rows = index // 2
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


def _preview_line(step: DraftStep, body: str) -> str:
    if step.condition is None or step.condition.is_empty():
        return body
    return f"{body}  |  if {step.condition.summary()}"


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
        actions = list(_condition_actions(step.condition))
        actions.append(
            {
                "type": "lco",
                "action": caps.lco_action if caps else f"tab_{tab}",
                "description": f"Open {caps.label if caps else tab} tab.",
            }
        )
        payload = _event_payload(
            event_id,
            title=f"Ensure {caps.label if caps else tab.title()}",
            description=f"Molecule Lab atom: open {tab} upgrade tab.",
            notes="Generated by Molecule Lab.",
            actions=actions,
        )
        return event_id, payload, _preview_line(step, f"ensure tab → {tab}")

    if step.kind == "molecule_ref":
        mol_id = step.molecule_id or ""
        if not mol_id:
            raise ComposerExpandError("molecule_ref step missing molecule_id")
        # Nested refs can't wrap decide without a generated shim yet — keep gate in preview/notes.
        return mol_id, None, _preview_line(step, f"reuse molecule → {mol_id}")

    if step.kind == "event_ref":
        event_id = step.event_id or ""
        if not event_id:
            raise ComposerExpandError("event_ref step missing event_id")
        return event_id, None, _preview_line(step, f"reuse atom → {event_id}")

    if step.kind == "seek_and_buy":
        tab = (step.tab or "").lower()
        caps = catalog.tabs.get(tab)
        label_slug = slug(step.label).replace("-", "_")
        event_id = f"composer_{molecule_slug}_{label_slug}"
        actions = _seek_buy_actions(step, caps)
        notes = (
            f"Generated by Molecule Lab.\n{_guard_note(step.guards)}\n"
            f"{_condition_note(step.condition)}\n"
            f"catalog_id={step.catalog_id} index={step.catalog_index}"
        )
        payload = _event_payload(
            event_id,
            title=f"Seek+Buy {step.label}",
            description=(
                f"Molecule Lab atom: relative-seek {step.label} on {tab.title()} "
                "then buy (skip maxed/unaffordable when perception supports it)."
            ),
            notes=notes,
            actions=actions,
        )
        guard_bits = ""
        if step.guards and step.guards.too_far_down:
            guard_bits = f" (guard down: {', '.join(step.guards.too_far_down)})"
        return event_id, payload, _preview_line(step, f"seek+buy → {step.label}{guard_bits}")

    raise ComposerExpandError(f"unknown step kind: {step.kind}")


def preview_expansion(draft: ComposerDraft, catalog: CapabilityCatalog) -> list[str]:
    lines: list[str] = [
        f"Molecule: {draft.title}",
        f"Phase: {draft.phase} · Kind: {draft.kind}",
    ]
    if not draft.steps:
        lines.append("(empty — click palette items to add steps)")
        return lines
    molecule_slug = slug(draft.title).replace("-", "_") or "molecule"
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
    collection_id = draft.collection_id or _slug_id("mol", title)

    root = Path(automations_root)
    events_dir = root / "events"
    collections_dir = root / "collections"
    events_dir.mkdir(parents=True, exist_ok=True)
    collections_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir(root).mkdir(parents=True, exist_ok=True)
    (root / "composer").mkdir(parents=True, exist_ok=True)

    children: list[str] = []
    event_paths: list[Path] = []
    preview = preview_expansion(draft, catalog)

    for i, step in enumerate(draft.steps, start=1):
        child_id, payload, _line = _expand_step(step, catalog, molecule_slug=molecule_slug, seq=i)
        children.append(child_id)
        if payload is not None:
            path = events_dir / f"{child_id}.json"
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            event_paths.append(path)

    requires = draft.requires_tab or next((s.tab for s in draft.steps if s.tab), None)
    condition_notes = [
        f"step {i}: {_condition_note(step.condition)}"
        for i, step in enumerate(draft.steps, start=1)
        if step.condition is not None and not step.condition.is_empty()
    ]
    collection = {
        "id": collection_id,
        "title": title,
        "version": 1,
        "description": (
            f"Molecule Lab · {draft.kind} · {draft.phase}"
            + (f" (requires {requires} tab)." if requires else ".")
        ),
        "children": children,
        "branch_variable": "phase",
        "branches": {},
        "loop": False,
        "stop_when": None,
        "run": "once",
        "notes": (
            "Authored via Molecule Lab. Files are source of truth.\n"
            + ("\n".join(condition_notes) if condition_notes else "No step conditions.")
        ),
    }
    collection_path = collections_dir / f"{collection_id}.json"
    collection_path.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")

    draft.collection_id = collection_id
    draft.title = title
    draft.requires_tab = requires
    draft_path = drafts_dir(root) / f"{collection_id}.json"
    draft_payload = draft.to_dict()
    # Preserve existing LCO placement when re-saving a molecule.
    if draft_path.exists():
        try:
            prior = json.loads(draft_path.read_text(encoding="utf-8"))
            if isinstance(prior, dict) and isinstance(prior.get("lco"), dict):
                draft_payload["lco"] = prior["lco"]
        except (OSError, json.JSONDecodeError):
            pass
    draft_path.write_text(json.dumps(draft_payload, indent=2) + "\n", encoding="utf-8")

    lib_path = library_path(root)
    # Persist only Lab-authored entries in library.json (collections still browsable via load_library).
    persisted: list[dict[str, Any]] = []
    if lib_path.exists():
        try:
            existing = json.loads(lib_path.read_text(encoding="utf-8"))
            raw = existing.get("molecules") if isinstance(existing, dict) else None
            if isinstance(raw, list):
                persisted = [m for m in raw if isinstance(m, dict) and str(m.get("id")) != collection_id]
        except (OSError, json.JSONDecodeError):
            persisted = []
    persisted.append(
        {
            "id": collection_id,
            "title": title,
            "requires_tab": requires,
            "description": collection["description"],
            "children": children,
            "phase": draft.phase,
            "kind": draft.kind,
            "source": "lab",
        }
    )
    lib_path.write_text(
        json.dumps({"version": 1, "molecules": persisted}, indent=2) + "\n",
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
