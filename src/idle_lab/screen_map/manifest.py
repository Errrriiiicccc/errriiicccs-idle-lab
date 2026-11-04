"""JSON manifest for a Screen Map batch folder."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class ShotRecord:
    index: int
    title: str
    filename: str
    captured_at: str
    anchor: dict[str, Any] | None = None
    classification: str | None = None
    how_opened: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShotRecord":
        return cls(
            index=int(data["index"]),
            title=str(data.get("title") or ""),
            filename=str(data.get("filename") or ""),
            captured_at=str(data.get("captured_at") or ""),
            anchor=data.get("anchor"),
            classification=data.get("classification"),
            how_opened=data.get("how_opened"),
            notes=data.get("notes"),
        )


@dataclass
class Manifest:
    batch_title: str
    batch_slug: str
    created_at: str
    shots: list[ShotRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_title": self.batch_title,
            "batch_slug": self.batch_slug,
            "created_at": self.created_at,
            "shots": [shot.to_dict() for shot in self.shots],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        shots = [ShotRecord.from_dict(item) for item in data.get("shots") or []]
        return cls(
            batch_title=str(data.get("batch_title") or ""),
            batch_slug=str(data.get("batch_slug") or ""),
            created_at=str(data.get("created_at") or ""),
            shots=shots,
        )


def manifest_path(folder: Path) -> Path:
    return Path(folder) / "manifest.json"


def load_manifest(folder: Path) -> Manifest:
    path = manifest_path(folder)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest.json root must be an object")
    return Manifest.from_dict(data)


def save_manifest(folder: Path, manifest: Manifest) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = manifest_path(folder)
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def new_manifest(batch_title: str, batch_slug: str) -> Manifest:
    return Manifest(
        batch_title=batch_title,
        batch_slug=batch_slug,
        created_at=_now_iso(),
        shots=[],
    )


def append_shot(manifest: Manifest, shot: ShotRecord) -> Manifest:
    """Return a new manifest with ``shot`` appended (immutable-ish helper)."""

    shots = list(manifest.shots)
    shots.append(shot)
    return Manifest(
        batch_title=manifest.batch_title,
        batch_slug=manifest.batch_slug,
        created_at=manifest.created_at,
        shots=shots,
    )
