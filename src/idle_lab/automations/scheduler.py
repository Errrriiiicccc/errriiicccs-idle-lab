"""Priority-aware interval scheduler.

Higher priority work hard-blocks lower priority events while it is running
(single-runway, non-preemptive). Overdue policies control catch-up vs skip.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from idle_lab.automations.schema import Event


@dataclass
class QueueItem:
    event_id: str
    title: str
    priority: int
    status: str  # waiting | running | deferred | skipped
    detail: str = ""


@dataclass
class Scheduler:
    """Tracks next-fire times and which event currently owns the worker."""

    clock: Callable[[], float] = time.monotonic
    _next_fire: dict[str, float] = field(default_factory=dict)
    _active_id: str | None = None
    _active_priority: int = -10**9
    _deferred: dict[str, str] = field(default_factory=dict)  # id → reason
    _skip_counts: dict[str, int] = field(default_factory=dict)
    _queue_view: list[QueueItem] = field(default_factory=list)
    _last_skip_messages: list[str] = field(default_factory=list)

    def reset(self, events: list[Event], *, stagger: bool = True) -> None:
        now = self.clock()
        self._next_fire.clear()
        self._active_id = None
        self._active_priority = -10**9
        self._deferred.clear()
        self._skip_counts.clear()
        self._last_skip_messages.clear()
        for index, event in enumerate(events):
            if not event.enabled:
                continue
            delay = (index * 0.25) if stagger else 0.0
            self._next_fire[event.id] = now + delay
        self._refresh_queue(events)

    def mark_running(self, event: Event) -> None:
        self._active_id = event.id
        self._active_priority = event.priority
        self._deferred.pop(event.id, None)

    def mark_finished(self, event: Event, events: list[Event]) -> None:
        now = self.clock()
        period = max(event.every_ms, 1) / 1000.0
        policy = getattr(event, "overdue_policy", "run_when_free") or "run_when_free"
        # Snap schedule forward according to policy after a real run.
        if policy == "run_once_catchup":
            # After catching up once, land on the next future slot from now.
            self._next_fire[event.id] = now + period
        else:
            self._next_fire[event.id] = now + period
        if self._active_id == event.id:
            self._active_id = None
            self._active_priority = -10**9
        self._deferred.pop(event.id, None)
        self._refresh_queue(events)

    def defer(self, event_id: str, reason: str = "blocked by higher priority") -> None:
        self._deferred[event_id] = reason

    @property
    def active_id(self) -> str | None:
        return self._active_id

    @property
    def active_priority(self) -> int:
        return self._active_priority

    def blocking_detail(self) -> str:
        if self._active_id:
            return f"blocked by {self._active_id}"
        return "blocked by higher priority"

    def take_skip_messages(self) -> list[str]:
        messages = list(self._last_skip_messages)
        self._last_skip_messages.clear()
        return messages

    def pick_due(self, events: list[Event]) -> Event | None:
        """Return the highest-priority due event that is allowed to run."""

        now = self.clock()
        enabled = [event for event in events if event.enabled and event.id in self._next_fire]
        due = [event for event in enabled if self._next_fire[event.id] <= now]
        due.sort(key=lambda event: (-event.priority, event.id))

        if self._active_id is not None:
            reason = self.blocking_detail()
            self._deferred = {
                event.id: reason for event in due if event.id != self._active_id
            }
            self._refresh_queue(events)
            return None

        if not due:
            self._deferred.clear()
            self._refresh_queue(events)
            return None

        # Apply skip policy for overdue events that lost the race this tick.
        chosen = due[0]
        still_due: list[Event] = [chosen]
        for event in due[1:]:
            policy = getattr(event, "overdue_policy", "run_when_free") or "run_when_free"
            if policy == "skip" and event.priority < chosen.priority:
                period = max(event.every_ms, 1) / 1000.0
                self._next_fire[event.id] = now + period
                count = self._skip_counts.get(event.id, 0) + 1
                self._skip_counts[event.id] = count
                self._last_skip_messages.append(
                    f"skipped {event.id} (overdue while {chosen.id} preferred); total skips={count}"
                )
                self._deferred.pop(event.id, None)
            else:
                still_due.append(event)
                if event.priority < chosen.priority:
                    self._deferred[event.id] = f"blocked by {chosen.id}"

        # Drop skip-losers from deferred noise
        for event in due[1:]:
            policy = getattr(event, "overdue_policy", "run_when_free") or "run_when_free"
            if policy == "skip" and event.priority < chosen.priority:
                continue

        self._refresh_queue(events)
        return chosen

    def queue_snapshot(self) -> list[QueueItem]:
        return list(self._queue_view)

    def deferred_summary(self) -> str:
        if not self._deferred:
            return ""
        parts = [f"{eid} ({reason})" for eid, reason in sorted(self._deferred.items())]
        return "; ".join(parts[:3]) + ("…" if len(parts) > 3 else "")

    def _refresh_queue(self, events: list[Event], running_hint: str | None = None) -> None:
        now = self.clock()
        items: list[QueueItem] = []
        active = running_hint if running_hint is not None else self._active_id
        for event in sorted(events, key=lambda item: (-item.priority, item.id)):
            if not event.enabled:
                continue
            if event.id == active:
                status = "running"
                detail = f"priority {event.priority}"
            elif event.id in self._deferred:
                status = "deferred"
                detail = self._deferred[event.id]
            else:
                fire_at = self._next_fire.get(event.id, now)
                wait_s = max(0.0, fire_at - now)
                status = "waiting"
                policy = getattr(event, "overdue_policy", "run_when_free") or "run_when_free"
                detail = f"in {wait_s:.1f}s · priority {event.priority}"
                if policy != "run_when_free":
                    detail += f" · {policy}"
                skips = self._skip_counts.get(event.id, 0)
                if skips:
                    detail += f" · skipped×{skips}"
            items.append(
                QueueItem(
                    event_id=event.id,
                    title=event.title,
                    priority=event.priority,
                    status=status,
                    detail=detail,
                )
            )
        self._queue_view = items


def recording_blocks_ab(active_priority: int, ab_priority: int) -> bool:
    """Pure helper used by tests: recording outranks the A/B tick."""

    return active_priority > ab_priority
