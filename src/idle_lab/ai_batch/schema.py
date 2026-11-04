"""JSON schema for AI information-gathering batches.

An external AI (or a human) drops ``batch.json`` folders under ``ai-batches/``.
Each batch names what should be collected (screenshots, events, screen-map
links, notes). The Idle Lab UI records completion + what was actually taken so
later chats can see gaps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

BATCH_STATUSES = ("pending", "running", "completed", "partial", "failed")
REQUEST_KINDS = (
    "screenshot",
    "screen_map_batch",
    "screen_map_shot",
    "event_snapshot",
    "collection_snapshot",
    "preset_list",
    "roi_dump",
    "note",
    "other",
)
REQUEST_STATUSES = ("pending", "done", "skipped", "missed")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass
class RequestResult:
    """What was actually gathered for a request."""

    summary: str = ""
    path: str | None = None
    screen_map_batch: str | None = None
    screen_map_shot: str | None = None
    event_id: str | None = None
    captured_at: str | None = None
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value is not None and value != ""}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RequestResult | None":
        if not data or not isinstance(data, dict):
            return None
        return cls(
            summary=str(data.get("summary") or ""),
            path=data.get("path"),
            screen_map_batch=data.get("screen_map_batch"),
            screen_map_shot=data.get("screen_map_shot"),
            event_id=data.get("event_id"),
            captured_at=data.get("captured_at"),
            payload=data.get("payload") if isinstance(data.get("payload"), dict) else None,
        )


# Executable step actions for AiBatchRunner (normalized coords = fractions of anchored window).
STEP_ACTIONS = (
    "wait",
    "click",
    "scroll",
    "scroll_map",
    "ensure_upgrade_tab",
    "screenshot",
    "play_preset",
)


@dataclass
class BatchRequest:
    id: str
    kind: str
    label: str
    detail: str = ""
    status: str = "pending"
    result: RequestResult | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "detail": self.detail,
            "status": self.status,
        }
        if self.steps:
            payload["steps"] = list(self.steps)
        if self.result is not None:
            payload["result"] = self.result.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchRequest":
        kind = str(data.get("kind") or "other")
        if kind not in REQUEST_KINDS:
            kind = "other"
        status = str(data.get("status") or "pending")
        if status not in REQUEST_STATUSES:
            status = "pending"
        raw_steps = data.get("steps") or []
        steps = [dict(item) for item in raw_steps if isinstance(item, dict)]
        return cls(
            id=str(data.get("id") or ""),
            kind=kind,
            label=str(data.get("label") or data.get("id") or "request"),
            detail=str(data.get("detail") or ""),
            status=status,
            result=RequestResult.from_dict(data.get("result") if isinstance(data.get("result"), dict) else None),
            steps=steps,
        )

    @property
    def runnable(self) -> bool:
        return bool(self.steps)


@dataclass
class FeedbackNote:
    at: str
    text: str
    author: str = "human"

    def to_dict(self) -> dict[str, Any]:
        return {"at": self.at, "text": self.text, "author": self.author}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackNote":
        return cls(
            at=str(data.get("at") or now_iso()),
            text=str(data.get("text") or ""),
            author=str(data.get("author") or "human"),
        )


@dataclass
class AiBatch:
    name: str
    slug: str
    status: str = "pending"
    goal: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None
    created_by: str = "ai"
    requests: list[BatchRequest] = field(default_factory=list)
    feedback: list[FeedbackNote] = field(default_factory=list)
    linked_screen_map_batches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "slug": self.slug,
            "status": self.status,
            "goal": self.goal,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "created_by": self.created_by,
            "requests": [item.to_dict() for item in self.requests],
            "feedback": [item.to_dict() for item in self.feedback],
            "linked_screen_map_batches": list(self.linked_screen_map_batches),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AiBatch":
        status = str(data.get("status") or "pending")
        if status not in BATCH_STATUSES:
            status = "pending"
        requests = [
            BatchRequest.from_dict(item)
            for item in (data.get("requests") or [])
            if isinstance(item, dict)
        ]
        feedback = [
            FeedbackNote.from_dict(item)
            for item in (data.get("feedback") or [])
            if isinstance(item, dict)
        ]
        linked = [str(item) for item in (data.get("linked_screen_map_batches") or [])]
        return cls(
            name=str(data.get("name") or data.get("slug") or "batch"),
            slug=str(data.get("slug") or ""),
            status=status,
            goal=str(data.get("goal") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            completed_at=data.get("completed_at"),
            created_by=str(data.get("created_by") or "ai"),
            requests=requests,
            feedback=feedback,
            linked_screen_map_batches=linked,
        )

    @property
    def done_count(self) -> int:
        return sum(1 for req in self.requests if req.status == "done")

    @property
    def request_count(self) -> int:
        return len(self.requests)

    def recompute_status(self) -> str:
        """Derive batch status from request statuses (does not mutate)."""

        if not self.requests:
            return self.status if self.status in BATCH_STATUSES else "pending"
        statuses = {req.status for req in self.requests}
        if statuses == {"done"} or (statuses <= {"done", "skipped"} and "done" in statuses):
            return "completed"
        if "done" in statuses or "missed" in statuses or "skipped" in statuses:
            return "partial"
        if self.status == "running":
            return "running"
        return "pending"


def new_batch(
    *,
    name: str,
    slug: str,
    goal: str = "",
    created_by: str = "human",
    requests: list[BatchRequest] | None = None,
) -> AiBatch:
    now = now_iso()
    return AiBatch(
        name=name,
        slug=slug,
        status="pending",
        goal=goal,
        created_at=now,
        updated_at=now,
        completed_at=None,
        created_by=created_by,
        requests=list(requests or []),
        feedback=[],
        linked_screen_map_batches=[],
    )


def touch(batch: AiBatch) -> AiBatch:
    batch.updated_at = now_iso()
    return batch
