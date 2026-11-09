"""T2 offline user stories — Lab APIs + temp dirs, no Tower / mouse."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from idle_lab.automations.store import AutomationStore
from idle_lab.automations.validate import (
    dry_run_collection,
    format_report,
    validate_project,
    validate_store,
)
from idle_lab.composer.catalog import load_capability_catalog
from idle_lab.composer.expand import expand_and_write, load_library
from idle_lab.composer.model import ComposerDraft, DraftStep, SeekGuards
from idle_lab.presets import PresetStore, project_root


class StoryError(RuntimeError):
    """Story failed or is unknown."""


@dataclass
class StoryResult:
    ok: bool
    story_id: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)


StoryHandler = Callable[[dict[str, Any], Path], StoryResult]


def stories_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "examples" / "harness-stories"


def list_stories(root: Path | None = None) -> list[dict[str, Any]]:
    folder = stories_dir(root)
    if not folder.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            out.append(
                {
                    "id": str(data.get("id") or path.stem),
                    "title": str(data.get("title") or path.stem),
                    "kind": str(data.get("kind") or ""),
                    "path": str(path),
                }
            )
    return out


def load_story(story_id: str, root: Path | None = None) -> dict[str, Any]:
    folder = stories_dir(root)
    path = folder / f"{story_id}.json"
    if not path.exists():
        # allow bare stem match
        matches = list(folder.glob(f"{story_id}*.json")) if folder.exists() else []
        if len(matches) == 1:
            path = matches[0]
        else:
            known = ", ".join(item["id"] for item in list_stories(root)) or "(none)"
            raise StoryError(f"unknown story {story_id!r}; known: {known}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoryError(f"unreadable story {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StoryError(f"story {path} must be an object")
    data.setdefault("id", story_id)
    data["_path"] = str(path)
    return data


def run_story(story_id: str, *, root: Path | None = None) -> StoryResult:
    project = root or project_root()
    story = load_story(story_id, project)
    kind = str(story.get("kind") or "").strip()
    handler = _HANDLERS.get(kind)
    if handler is None:
        raise StoryError(f"story {story_id!r} has unknown kind {kind!r}")
    return handler(story, project)


def _story_composer_save_roundtrip(story: dict[str, Any], root: Path) -> StoryResult:
    catalog = load_capability_catalog(root)
    params = story.get("params") if isinstance(story.get("params"), dict) else {}
    tab_name = str(params.get("tab") or "attack").lower()
    tab = catalog.tabs.get(tab_name)
    if tab is None:
        return StoryResult(
            ok=False,
            story_id=str(story.get("id")),
            summary=f"unknown tab {tab_name!r} in capability catalog",
        )

    labels = params.get("buy_labels") or ["Damage"]
    if not isinstance(labels, list) or not labels:
        labels = ["Damage"]

    title = str(params.get("title") or story.get("title") or "Harness composer molecule")
    draft = ComposerDraft(title=title)
    draft.add_step(DraftStep(kind="ensure_tab", label=tab_name.title(), tab=tab_name))

    for label in labels:
        entry = next((e for e in tab.catalog if e.label == label), None)
        if entry is None:
            # soft match
            entry = next(
                (e for e in tab.catalog if label.casefold() in e.label.casefold()),
                None,
            )
        if entry is None:
            return StoryResult(
                ok=False,
                story_id=str(story.get("id")),
                summary=f"catalog missing buy label {label!r} on tab {tab_name}",
            )
        draft.add_step(
            DraftStep(
                kind="seek_and_buy",
                label=entry.label,
                tab=tab_name,
                catalog_id=entry.id,
                catalog_index=entry.index,
                guards=tab.guards_for(entry) if entry.index >= 6 else SeekGuards(),
            )
        )

    with tempfile.TemporaryDirectory(prefix="idle-lab-story-composer-") as folder:
        auto_root = Path(folder)
        (auto_root / "events").mkdir()
        (auto_root / "collections").mkdir()
        result = expand_and_write(draft, automations_root=auto_root, catalog=catalog)

        checks: dict[str, Any] = {
            "collection_path": str(result.collection_path),
            "collection_exists": result.collection_path.exists(),
            "event_count": len(result.event_paths),
            "events_exist": all(p.exists() for p in result.event_paths),
            "collection_id": result.collection_id,
        }
        payload = json.loads(result.collection_path.read_text(encoding="utf-8"))
        checks["children"] = payload.get("children")
        checks["run"] = payload.get("run")

        lib = load_library(auto_root)
        checks["library_has_molecule"] = any(m.get("id") == result.collection_id for m in lib)
        lib_entry = next((m for m in lib if m.get("id") == result.collection_id), None)
        checks["requires_tab"] = (lib_entry or {}).get("requires_tab")

        store = AutomationStore(auto_root)
        load_errors = store.load_all()
        checks["load_errors"] = load_errors
        validation = validate_store(store)
        checks["validation_ok"] = validation.ok
        checks["validation"] = format_report(validation)

        dry_lines: list[str] = []
        if result.collection_id in store.collections:
            dry_lines = dry_run_collection(store.collections[result.collection_id], store)
            checks["dry_run_lines"] = len(dry_lines)

        ok = (
            checks["collection_exists"]
            and checks["events_exist"]
            and checks["library_has_molecule"]
            and not load_errors
            and validation.ok
            and checks.get("requires_tab") == tab_name
        )
        summary = (
            f"composer expand wrote {result.collection_id} "
            f"({checks['event_count']} events); library+validate "
            + ("ok" if ok else "FAILED")
        )
        return StoryResult(
            ok=ok,
            story_id=str(story.get("id")),
            summary=summary,
            details=checks,
            lines=dry_lines[:40],
        )


def _story_molecule_dry_run(story: dict[str, Any], root: Path) -> StoryResult:
    params = story.get("params") if isinstance(story.get("params"), dict) else {}
    collection_id = str(params.get("collection_id") or "health_then_damage").strip()
    store = AutomationStore(root / "automations")
    errors = store.load_all()
    collection = store.collections.get(collection_id)
    if collection is None:
        return StoryResult(
            ok=False,
            story_id=str(story.get("id")),
            summary=f"collection {collection_id!r} not found",
            details={"load_errors": errors, "known": sorted(store.collections)},
        )
    lines = dry_run_collection(collection, store)
    validation = validate_store(store)
    ok = validation.ok and not any("MISSING" in line for line in lines)
    return StoryResult(
        ok=ok,
        story_id=str(story.get("id")),
        summary=f"dry-run {collection_id}: {len(lines)} plan lines; validate "
        + ("ok" if validation.ok else "FAILED"),
        details={
            "collection_id": collection_id,
            "validation": format_report(validation),
            "load_errors": errors,
        },
        lines=lines,
    )


def _story_schema_validate_all(story: dict[str, Any], root: Path) -> StoryResult:
    presets = PresetStore(root / "presets")
    presets.load_all()
    preset_names = {preset.name for preset in presets.presets}
    report = validate_project(root, preset_names=preset_names)
    text = format_report(report)
    return StoryResult(
        ok=report.ok,
        story_id=str(story.get("id")),
        summary=text.splitlines()[0] if text else "validate",
        details={
            "issue_count": len(report.issues),
            "issues": [
                {"level": i.level, "path": i.path, "message": i.message} for i in report.issues
            ],
        },
        lines=text.splitlines(),
    )


_HANDLERS: dict[str, StoryHandler] = {
    "composer_save_roundtrip": _story_composer_save_roundtrip,
    "molecule_dry_run": _story_molecule_dry_run,
    "schema_validate_all": _story_schema_validate_all,
}
