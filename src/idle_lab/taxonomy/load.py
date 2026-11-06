"""Load and resolve automations/taxonomy.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Collection

from idle_lab.flight_deck.actions import ActionError, normalize_action
from idle_lab.flight_deck.keys import BACK_TOKEN, DESCRIBE_TOKEN, normalize_menu_key
from idle_lab.taxonomy.model import Taxonomy, TaxonomyError, TaxonomyNode

_RESERVED = {normalize_menu_key(BACK_TOKEN), normalize_menu_key(DESCRIBE_TOKEN)}
_REF_KINDS = frozenset({"event", "collection", "preset"})


def default_taxonomy_path(project_root: Path) -> Path:
    return project_root / "automations" / "taxonomy.json"


def load_taxonomy(path: Path) -> Taxonomy:
    if not path.exists():
        raise TaxonomyError(f"Missing taxonomy file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise TaxonomyError(f"Unreadable taxonomy: {exc}") from exc
    if not isinstance(data, dict):
        raise TaxonomyError("Taxonomy root must be an object")
    version = int(data.get("version", 1))
    if version != 1:
        raise TaxonomyError(f"Unsupported taxonomy version: {version}")
    roots_raw = data.get("roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise TaxonomyError("roots must be a non-empty list")
    seen_ids: set[str] = set()
    roots = [_parse_node(item, f"roots[{i}]", seen_ids) for i, item in enumerate(roots_raw)]
    return Taxonomy(version=version, roots=roots, path=path)


def resolve_taxonomy(
    taxonomy: Taxonomy,
    *,
    event_ids: Collection[str],
    collection_ids: Collection[str],
    preset_names: Collection[str],
) -> Taxonomy:
    """Return a copy with refs expanded to actions; validate targets exist."""

    events = set(event_ids)
    collections = set(collection_ids)
    presets = set(preset_names)

    def resolve_node(node: TaxonomyNode) -> TaxonomyNode:
        children = [resolve_node(child) for child in node.children]
        action = dict(node.action) if node.action else None
        if node.ref is not None:
            if action is not None:
                raise TaxonomyError(f"{node.id}: cannot have both ref and action")
            action = _action_from_ref(node.ref, node.id, events, collections, presets)
        if not children and action is None:
            raise TaxonomyError(f"{node.id}: leaf needs action or ref")
        return TaxonomyNode(
            id=node.id,
            key=node.key,
            label=node.label,
            description=node.description,
            children=children,
            action=action,
            ref=None if action else node.ref,
        )

    return Taxonomy(
        version=taxonomy.version,
        roots=[resolve_node(root) for root in taxonomy.roots],
        path=taxonomy.path,
    )


def _action_from_ref(
    ref: dict[str, str],
    where: str,
    events: set[str],
    collections: set[str],
    presets: set[str],
) -> dict[str, Any]:
    kind = str(ref.get("kind") or "").strip()
    target = str(ref.get("id") or "").strip()
    if kind not in _REF_KINDS:
        raise TaxonomyError(f"{where}.ref.kind must be one of {sorted(_REF_KINDS)}")
    if not target:
        raise TaxonomyError(f"{where}.ref.id is required")
    if kind == "event":
        if target not in events:
            raise TaxonomyError(f"{where}: unknown event id {target!r}")
        return {"type": "start_event", "event": target}
    if kind == "collection":
        if target not in collections:
            raise TaxonomyError(f"{where}: unknown collection id {target!r}")
        return {"type": "start_collection", "collection": target}
    if target not in presets:
        raise TaxonomyError(f"{where}: unknown preset name {target!r}")
    return {"type": "play_preset", "preset": target}


def _parse_node(raw: Any, where: str, seen_ids: set[str]) -> TaxonomyNode:
    if not isinstance(raw, dict):
        raise TaxonomyError(f"{where} must be an object")
    node_id = str(raw.get("id", "")).strip()
    key = str(raw.get("key", "")).strip()
    label = str(raw.get("label", "")).strip()
    description = str(raw.get("description") or "").strip()
    if not node_id:
        raise TaxonomyError(f"{where}.id is required")
    if node_id in seen_ids:
        raise TaxonomyError(f"{where}: duplicate id {node_id!r}")
    seen_ids.add(node_id)
    if not key:
        raise TaxonomyError(f"{where}.key is required")
    if not label:
        raise TaxonomyError(f"{where}.label is required")
    norm = normalize_menu_key(key)
    if norm in _RESERVED:
        raise TaxonomyError(f"{where}.key {key!r} is reserved for the flight-deck host")

    children_raw = raw.get("children") or []
    if children_raw is None:
        children_raw = []
    if not isinstance(children_raw, list):
        raise TaxonomyError(f"{where}.children must be a list")
    children = [
        _parse_node(item, f"{where}.children[{i}]", seen_ids) for i, item in enumerate(children_raw)
    ]

    action_raw = raw.get("action")
    ref_raw = raw.get("ref")
    if action_raw is not None and ref_raw is not None:
        raise TaxonomyError(f"{where} cannot have both action and ref")
    if children and (action_raw is not None or ref_raw is not None):
        raise TaxonomyError(f"{where} cannot have both children and action/ref")
    if not children and action_raw is None and ref_raw is None:
        raise TaxonomyError(f"{where} leaf needs an action or ref")

    action: dict[str, Any] | None = None
    if action_raw is not None:
        if not isinstance(action_raw, dict):
            raise TaxonomyError(f"{where}.action must be an object")
        try:
            action = normalize_action(action_raw)
        except ActionError as exc:
            raise TaxonomyError(f"{where}.action: {exc}") from exc

    ref: dict[str, str] | None = None
    if ref_raw is not None:
        if not isinstance(ref_raw, dict):
            raise TaxonomyError(f"{where}.ref must be an object")
        kind = str(ref_raw.get("kind") or "").strip()
        target = str(ref_raw.get("id") or "").strip()
        if kind not in _REF_KINDS:
            raise TaxonomyError(f"{where}.ref.kind must be one of {sorted(_REF_KINDS)}")
        if not target:
            raise TaxonomyError(f"{where}.ref.id is required")
        ref = {"kind": kind, "id": target}

    # Sibling key uniqueness within this folder.
    seen_keys: set[str] = set()
    for child in children:
        ck = normalize_menu_key(child.key)
        if ck in seen_keys:
            raise TaxonomyError(f"{where}: duplicate child key {child.key!r}")
        seen_keys.add(ck)

    return TaxonomyNode(
        id=node_id,
        key=key,
        label=label,
        description=description,
        children=children,
        action=action,
        ref=ref,
    )
