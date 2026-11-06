"""Hierarchical lab comments keyed by object path (presets, batches, shots, …)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class CommentEntry:
    text: str
    updated_at: str

    def to_dict(self) -> dict[str, str]:
        return {"text": self.text, "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, data: object) -> "CommentEntry | None":
        if not isinstance(data, dict):
            return None
        text = str(data.get("text") or "")
        if not text.strip():
            return None
        return cls(text=text, updated_at=str(data.get("updated_at") or ""))


class CommentStore:
    """File-backed notes. Paths are stable lab object keys, e.g. ``presets/foo``."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._entries: dict[str, CommentEntry] = {}

    def load(self) -> list[str]:
        """Reload from disk. Returns skip/error messages."""

        errors: list[str] = []
        self._entries = {}
        if not self.path.exists():
            return errors
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return [f"lab-comments.json: {exc}"]
        if not isinstance(raw, dict):
            return ["lab-comments.json: root must be an object"]
        for key, value in raw.items():
            entry = CommentEntry.from_dict(value)
            if entry is not None:
                self._entries[str(key)] = entry
        return errors

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: entry.to_dict() for key, entry in sorted(self._entries.items())}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def get(self, object_path: str) -> str:
        entry = self._entries.get(object_path)
        return entry.text if entry else ""

    def has(self, object_path: str) -> bool:
        return bool(self.get(object_path).strip())

    def set(self, object_path: str, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            self._entries.pop(object_path, None)
        else:
            self._entries[object_path] = CommentEntry(text=cleaned, updated_at=_now_iso())
        self.save()


def preset_comment_path(slug_or_stem: str) -> str:
    return f"presets/{slug_or_stem}"


def mission_comment_path(slug: str) -> str:
    return f"ai-batches/{slug}"


def mission_request_comment_path(slug: str, request_id: str) -> str:
    return f"ai-batches/{slug}/req/{request_id}"


def event_comment_path(event_id: str) -> str:
    return f"automations/events/{event_id}"


def collection_comment_path(collection_id: str) -> str:
    return f"automations/collections/{collection_id}"


def screen_map_batch_comment_path(slug: str) -> str:
    return f"screen-maps/{slug}"


def screen_map_shot_comment_path(slug: str, filename: str) -> str:
    return f"screen-maps/{slug}/shots/{filename}"
