"""Load workspace lab-context.json — baked target assumptions for the harness."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.presets import project_root


class LabContextError(ValueError):
    """lab-context.json is missing or invalid."""


@dataclass(frozen=True)
class TargetProfile:
    id: str
    label: str
    anchor_title_substrings: tuple[str, ...] = ()
    prefer_last_anchor: bool = True
    object_map: str | None = None
    playbook: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "anchor_title_substrings": list(self.anchor_title_substrings),
            "prefer_last_anchor": self.prefer_last_anchor,
            "object_map": self.object_map,
            "playbook": self.playbook,
        }


@dataclass(frozen=True)
class LabContext:
    version: int
    active_target: str
    targets: dict[str, TargetProfile] = field(default_factory=dict)
    path: Path | None = None

    @property
    def target(self) -> TargetProfile:
        profile = self.targets.get(self.active_target)
        if profile is None:
            raise LabContextError(
                f"active_target {self.active_target!r} not found in lab-context targets"
            )
        return profile

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "active_target": self.active_target,
            "targets": {key: value.as_dict() for key, value in self.targets.items()},
            "path": str(self.path) if self.path else None,
        }


def context_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "lab-context.json"


def load_lab_context(root: Path | None = None) -> LabContext:
    path = context_path(root)
    if not path.exists():
        raise LabContextError(f"missing lab-context.json at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabContextError(f"unreadable lab-context.json: {exc}") from exc
    if not isinstance(data, dict):
        raise LabContextError("lab-context.json must be an object")

    version = int(data.get("version") or 1)
    active = str(data.get("active_target") or "").strip()
    if not active:
        raise LabContextError("lab-context.json needs active_target")

    raw_targets = data.get("targets")
    if not isinstance(raw_targets, dict) or not raw_targets:
        raise LabContextError("lab-context.json needs a non-empty targets object")

    targets: dict[str, TargetProfile] = {}
    for key, raw in raw_targets.items():
        tid = str(key).strip()
        if not tid or not isinstance(raw, dict):
            continue
        subs = raw.get("anchor_title_substrings") or []
        if not isinstance(subs, list):
            raise LabContextError(f"target {tid}: anchor_title_substrings must be a list")
        targets[tid] = TargetProfile(
            id=tid,
            label=str(raw.get("label") or tid).strip() or tid,
            anchor_title_substrings=tuple(
                str(item).strip() for item in subs if str(item).strip()
            ),
            prefer_last_anchor=bool(raw.get("prefer_last_anchor", True)),
            object_map=(str(raw["object_map"]).strip() if raw.get("object_map") else None),
            playbook=(str(raw["playbook"]).strip() if raw.get("playbook") else None),
        )

    if active not in targets:
        raise LabContextError(f"active_target {active!r} not in targets")

    return LabContext(version=version, active_target=active, targets=targets, path=path)
