"""Load automations JSON trees from disk."""

from __future__ import annotations

import json
from pathlib import Path

from idle_lab.automations.schema import (
    AutomationSchemaError,
    Collection,
    Event,
    Roi,
    RuntimeConfig,
    collection_from_dict,
    event_from_dict,
    roi_from_dict,
    runtime_from_dict,
)


class AutomationStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.rois: dict[str, Roi] = {}
        self.events: dict[str, Event] = {}
        self.collections: dict[str, Collection] = {}
        self.runtime = RuntimeConfig()
        self.errors: list[str] = []

    def load_all(self) -> list[str]:
        self.rois.clear()
        self.events.clear()
        self.collections.clear()
        self.errors = []
        self.runtime = RuntimeConfig()

        runtime_path = self.root / "runtime.json"
        if runtime_path.exists():
            try:
                data = json.loads(runtime_path.read_text(encoding="utf-8"))
                self.runtime = runtime_from_dict(data, str(runtime_path))
            except (OSError, json.JSONDecodeError, AutomationSchemaError) as exc:
                self.errors.append(f"{runtime_path.name}: {exc}")

        self._load_map(self.root / "rois", roi_from_dict, self.rois, "roi")
        self._load_map(self.root / "events", event_from_dict, self.events, "event")
        self._load_map(self.root / "collections", collection_from_dict, self.collections, "collection")
        return list(self.errors)

    def _load_map(self, folder: Path, loader, target: dict, kind: str) -> None:
        if not folder.exists():
            return
        for path in sorted(folder.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                item = loader(data, str(path))
                item_id = getattr(item, "id")
                if item_id in target:
                    self.errors.append(f"{path.name}: duplicate {kind} id {item_id}")
                    continue
                target[item_id] = item
            except (OSError, json.JSONDecodeError, AutomationSchemaError) as exc:
                self.errors.append(f"{path.name}: {exc}")
