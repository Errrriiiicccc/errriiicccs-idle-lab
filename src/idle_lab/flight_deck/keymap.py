"""File-backed nested hotkey tree for the flight deck."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class KeymapError(ValueError):
    """flight_deck_keymap.json does not match the v1 contract."""


@dataclass
class KeymapNode:
    key: str
    label: str
    description: str = ""
    children: list[KeymapNode] = field(default_factory=list)
    action: dict[str, Any] | None = None

    @property
    def is_leaf(self) -> bool:
        return not self.children


@dataclass
class FlightDeckKeymap:
    version: int
    roots: list[KeymapNode]
    path: Path | None = None

    def child_for_key(self, nodes: list[KeymapNode], token: str) -> KeymapNode | None:
        from idle_lab.flight_deck.keys import normalize_menu_key

        want = normalize_menu_key(token)
        if not want:
            return None
        for node in nodes:
            if normalize_menu_key(node.key) == want:
                return node
        return None


def _parse_node(raw: Any, where: str) -> KeymapNode:
    if not isinstance(raw, dict):
        raise KeymapError(f"{where} must be an object")
    key = str(raw.get("key", "")).strip()
    label = str(raw.get("label", "")).strip()
    description = str(raw.get("description") or "").strip()
    if not key:
        raise KeymapError(f"{where}.key is required")
    if not label:
        raise KeymapError(f"{where}.label is required")
    children_raw = raw.get("children") or []
    if children_raw is None:
        children_raw = []
    if not isinstance(children_raw, list):
        raise KeymapError(f"{where}.children must be a list")
    children = [_parse_node(item, f"{where}.children[{i}]") for i, item in enumerate(children_raw)]
    action = raw.get("action")
    if action is not None and not isinstance(action, dict):
        raise KeymapError(f"{where}.action must be an object")
    if children and action is not None:
        raise KeymapError(f"{where} cannot have both children and action")
    if not children and action is None:
        raise KeymapError(f"{where} leaf needs an action")
    if action is not None:
        from idle_lab.flight_deck.actions import ActionError, normalize_action

        try:
            action = normalize_action(action)
        except ActionError as exc:
            raise KeymapError(f"{where}.action: {exc}") from exc
    return KeymapNode(
        key=key,
        label=label,
        description=description,
        children=children,
        action=action,
    )


def load_keymap(path: Path) -> FlightDeckKeymap:
    if not path.exists():
        raise KeymapError(f"Missing keymap file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise KeymapError(f"Unreadable keymap: {exc}") from exc
    if not isinstance(data, dict):
        raise KeymapError("Keymap root must be an object")
    version = int(data.get("version", 1))
    if version != 1:
        raise KeymapError(f"Unsupported keymap version: {version}")
    roots_raw = data.get("roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise KeymapError("roots must be a non-empty list")
    roots = [_parse_node(item, f"roots[{i}]") for i, item in enumerate(roots_raw)]
    return FlightDeckKeymap(version=version, roots=roots, path=path)


def default_keymap_path(project_root: Path) -> Path:
    """In-flight accordion catalog (separate from Lab Loops taxonomy)."""

    return project_root / "automations" / "flight_deck.json"
