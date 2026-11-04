"""Load / save AI information batches under ``ai-batches/<slug>/batch.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from idle_lab.ai_batch.schema import (
    AiBatch,
    BatchRequest,
    FeedbackNote,
    RequestResult,
    new_batch,
    now_iso,
    touch,
)
from idle_lab.screen_map.names import sanitize_slug, unique_dir


class AiBatchError(RuntimeError):
    """User-facing AI batch failure."""


def batch_path(folder: Path) -> Path:
    return Path(folder) / "batch.json"


class AiBatchStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.batches: dict[str, AiBatch] = {}
        self.folders: dict[str, Path] = {}

    def load_all(self) -> list[str]:
        """Reload every ``*/batch.json``. Returns skip errors."""

        self.root.mkdir(parents=True, exist_ok=True)
        self.batches.clear()
        self.folders.clear()
        errors: list[str] = []
        for folder in sorted(self.root.iterdir() if self.root.exists() else [], key=lambda p: p.name.lower()):
            if not folder.is_dir():
                continue
            path = batch_path(folder)
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("root must be an object")
                batch = AiBatch.from_dict(data)
                if not batch.slug:
                    batch.slug = folder.name
                self.batches[batch.slug] = batch
                self.folders[batch.slug] = folder
            except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
                errors.append(f"{folder.name}: {exc}")
        return errors

    def list_batches(
        self,
        *,
        status_filter: str = "all",
        sort_key: str = "updated",
    ) -> list[AiBatch]:
        items = list(self.batches.values())
        if status_filter and status_filter != "all":
            if status_filter == "completed":
                items = [b for b in items if b.status == "completed"]
            elif status_filter == "open":
                items = [b for b in items if b.status in ("pending", "running", "partial")]
            else:
                items = [b for b in items if b.status == status_filter]

        def key_fn(batch: AiBatch):
            if sort_key == "name":
                return batch.name.lower()
            if sort_key == "created":
                return batch.created_at or ""
            if sort_key == "status":
                return (batch.status, batch.updated_at or "")
            # updated (default) — newest first via reverse later
            return batch.updated_at or batch.created_at or ""

        reverse = sort_key in ("updated", "created")
        return sorted(items, key=key_fn, reverse=reverse)

    def create(
        self,
        name: str,
        *,
        goal: str = "",
        created_by: str = "human",
        requests: list[dict[str, Any]] | None = None,
    ) -> AiBatch:
        title = (name or "").strip()
        if not title:
            raise AiBatchError("Batch name is required.")
        slug_base = sanitize_slug(title, fallback="ai-batch")
        folder = unique_dir(self.root, slug_base)
        folder.mkdir(parents=True, exist_ok=False)
        reqs: list[BatchRequest] = []
        for index, raw in enumerate(requests or [], start=1):
            if not isinstance(raw, dict):
                continue
            payload = dict(raw)
            payload.setdefault("id", f"req-{index}")
            payload.setdefault("label", payload["id"])
            reqs.append(BatchRequest.from_dict(payload))
        batch = new_batch(name=title, slug=folder.name, goal=goal, created_by=created_by, requests=reqs)
        self._write(folder, batch)
        self.batches[batch.slug] = batch
        self.folders[batch.slug] = folder
        return batch

    def save(self, batch: AiBatch) -> Path:
        folder = self.folders.get(batch.slug)
        if folder is None:
            folder = self.root / batch.slug
            folder.mkdir(parents=True, exist_ok=True)
            self.folders[batch.slug] = folder
        touch(batch)
        path = self._write(folder, batch)
        self.batches[batch.slug] = batch
        return path

    def folder_for(self, slug: str) -> Path | None:
        return self.folders.get(slug)

    def mark_request(
        self,
        batch: AiBatch,
        request_id: str,
        *,
        status: str,
        result: RequestResult | None = None,
    ) -> AiBatch:
        found = False
        for req in batch.requests:
            if req.id == request_id:
                req.status = status
                if result is not None:
                    req.result = result
                found = True
                break
        if not found:
            raise AiBatchError(f"Unknown request id: {request_id}")
        batch.status = batch.recompute_status()
        if batch.status == "completed" and not batch.completed_at:
            batch.completed_at = now_iso()
        self.save(batch)
        return batch

    def add_feedback(self, batch: AiBatch, text: str, *, author: str = "human") -> AiBatch:
        note = (text or "").strip()
        if not note:
            raise AiBatchError("Feedback text is required.")
        batch.feedback.append(FeedbackNote(at=now_iso(), text=note, author=author))
        self.save(batch)
        return batch

    def link_screen_map(self, batch: AiBatch, screen_map_slug: str) -> AiBatch:
        slug = (screen_map_slug or "").strip()
        if not slug:
            raise AiBatchError("Screen Map batch slug is required.")
        if slug not in batch.linked_screen_map_batches:
            batch.linked_screen_map_batches.append(slug)
        self.save(batch)
        return batch

    def snapshot_event(self, store_events: dict, event_id: str) -> dict[str, Any]:
        event = store_events.get(event_id)
        if event is None:
            raise AiBatchError(f"Event not found: {event_id}")
        return {
            "id": event.id,
            "title": event.title,
            "priority": event.priority,
            "every_ms": event.every_ms,
            "enabled": event.enabled,
            "description": event.description,
            "notes": event.notes,
            "actions": event.actions,
        }

    def _write(self, folder: Path, batch: AiBatch) -> Path:
        path = batch_path(folder)
        path.write_text(json.dumps(batch.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path


def create_from_ai_spec(root: Path, spec: dict[str, Any]) -> AiBatch:
    """Hook entry: AI writes a dict (or we load one) and materialize a batch folder."""

    store = AiBatchStore(root)
    store.load_all()
    name = str(spec.get("name") or "").strip()
    if not name:
        raise AiBatchError("AI batch spec requires 'name'.")
    return store.create(
        name,
        goal=str(spec.get("goal") or ""),
        created_by=str(spec.get("created_by") or "ai"),
        requests=list(spec.get("requests") or []),
    )
