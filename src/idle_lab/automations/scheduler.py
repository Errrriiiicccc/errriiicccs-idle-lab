"""Priority-aware interval scheduler.

Higher priority work hard-blocks lower priority events while it is running.
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
    status: str  # waiting | running | deferred | done
    detail: str = ""


@dataclass
class Scheduler:
    """Tracks next-fire times and which event currently owns the worker."""

    clock: Callable[[], float] = time.monotonic
    _next_fire: dict[str, float] = field(default_factory=dict)
    _active_id: str | None = None
    _active_priority: int = -10**9
    _deferred: set[str] = field(default_factory=set)
    _queue_view: list[QueueItem] = field(default_factory=list)

    def reset(self, events: list[Event], *, stagger: bool = True) -> None:
        now = self.clock()
        self._next_fire.clear()
        self._active_id = None
        self._active_priority = -10**9
        self._deferred.clear()
        for index, event in enumerate(events):
            if not event.enabled:
                continue
            # Stagger first fires slightly so UI isn't flooded at t=0.
            delay = (index * 0.25) if stagger else 0.0
            self._next_fire[event.id] = now + delay
        self._refresh_queue(events)

    def mark_running(self, event: Event) -> None:
        self._active_id = event.id
        self._active_priority = event.priority
        self._deferred.discard(event.id)

    def mark_finished(self, event: Event, events: list[Event]) -> None:
        now = self.clock()
        self._next_fire[event.id] = now + max(event.every_ms, 1) / 1000.0
        if self._active_id == event.id:
            self._active_id = None
            self._active_priority = -10**9
        self._deferred.discard(event.id)
        self._refresh_queue(events)

    def defer(self, event_id: str, reason: str = "blocked by higher priority") -> None:
        self._deferred.add(event_id)

    @property
    def active_id(self) -> str | None:
        return self._active_id

    @property
    def active_priority(self) -> int:
        return self._active_priority

    def pick_due(self, events: list[Event]) -> Event | None:
        """Return the highest-priority due event that is allowed to run."""

        now = self.clock()
        enabled = [event for event in events if event.enabled and event.id in self._next_fire]
        due = [event for event in enabled if self._next_fire[event.id] <= now]
        due.sort(key=lambda event: (-event.priority, event.id))

        if self._active_id is not None:
            # Hard block: nothing else runs while an event owns the worker.
            self._deferred = {event.id for event in due if event.id != self._active_id}
            self._refresh_queue(events)
            return None

        if not due:
            self._deferred.clear()
            self._refresh_queue(events)
            return None

        chosen = due[0]
        for event in due[1:]:
            if event.priority < chosen.priority:
                self._deferred.add(event.id)
        self._refresh_queue(events, running_hint=None)
        return chosen

    def queue_snapshot(self) -> list[QueueItem]:
        return list(self._queue_view)

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
                detail = "blocked by higher priority"
            else:
                fire_at = self._next_fire.get(event.id, now)
                wait_s = max(0.0, fire_at - now)
                status = "waiting"
                detail = f"in {wait_s:.1f}s · priority {event.priority}"
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
