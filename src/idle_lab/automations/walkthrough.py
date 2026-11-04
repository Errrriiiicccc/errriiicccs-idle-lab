"""Collection Walkthrough — guided review of events/branches without running them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from idle_lab.automations.describe import _action_description, _event_blurb, list_caption
from idle_lab.automations.guide_overlay import GuideCard, GuideChoice
from idle_lab.automations.schema import Action, Collection, Event
from idle_lab.automations.store import AutomationStore

StepKind = Literal["intro", "event", "event_branch", "collection_branch", "path_preview", "done"]


@dataclass
class WalkStep:
    kind: StepKind
    title: str
    body: str
    hint: str
    choices: list[GuideChoice] = field(default_factory=list)
    branch_targets: dict[str, Any] = field(default_factory=dict)
    accent: str = "#8EE0C2"


@dataclass
class _Frame:
    collection: Collection
    child_index: int = 0
    phase: str = "intro"  # intro | children | branches | done


class Walkthrough:
    """Stateful guided tour of a root collection."""

    def __init__(self, store: AutomationStore, root: Collection) -> None:
        self.store = store
        self.root = root
        self.active = False
        self._stack: list[_Frame] = []
        self._current: WalkStep | None = None
        self._return_to_branches = False

    @property
    def current(self) -> WalkStep | None:
        return self._current

    def start(self) -> WalkStep:
        self.active = True
        self._stack = [_Frame(collection=self.root, phase="intro")]
        self._return_to_branches = False
        self._current = self._intro_step(self.root)
        return self._current

    def stop(self) -> None:
        self.active = False
        self._stack.clear()
        self._current = None
        self._return_to_branches = False

    def advance_space(self) -> WalkStep | None:
        if not self.active or self._current is None:
            return None
        kind = self._current.kind
        if kind == "event_branch":
            return self._current  # must pick A/B
        if kind == "path_preview":
            return self._after_linear_item()
        if kind == "collection_branch":
            # Space skips remaining branch exploration for this collection.
            if self._stack:
                self._stack[-1].phase = "done"
            return self._leave_frame()
        if kind == "done":
            self.stop()
            return None
        if kind == "intro":
            if self._stack:
                self._stack[-1].phase = "children"
            return self._progress()
        if kind == "event":
            return self._after_linear_item()
        return self._progress()

    def choose(self, key: str) -> WalkStep | None:
        if not self.active or self._current is None:
            return None
        key = key.upper()
        if key not in self._current.branch_targets:
            return self._current
        target = self._current.branch_targets[key]
        if self._current.kind == "event_branch":
            self._current = self._path_preview_step(key, target)
            return self._current
        if self._current.kind == "collection_branch":
            return self._enter_child(target, from_branches=True)
        return self._current

    def to_card(self) -> GuideCard | None:
        step = self._current
        if step is None:
            return None
        return GuideCard(
            title=step.title,
            body=step.body,
            hint=step.hint,
            choices=list(step.choices),
            accent=step.accent,
        )

    def _after_linear_item(self) -> WalkStep:
        if self._return_to_branches:
            self._return_to_branches = False
            if self._stack:
                self._stack[-1].phase = "branches"
            return self._progress()
        if self._stack:
            self._stack[-1].child_index += 1
        return self._progress()

    def _progress(self) -> WalkStep:
        while self._stack:
            frame = self._stack[-1]
            if frame.phase == "intro":
                self._current = self._intro_step(frame.collection)
                return self._current
            if frame.phase == "children":
                children = frame.collection.children
                if frame.child_index < len(children):
                    return self._enter_child(children[frame.child_index], from_branches=False)
                frame.phase = "branches" if frame.collection.branches else "done"
                continue
            if frame.phase == "branches":
                if frame.collection.branches:
                    self._current = self._collection_branch_step(frame.collection)
                    return self._current
                frame.phase = "done"
                continue
            # done
            return self._leave_frame()
        self._current = self._done_step()
        return self._current

    def _leave_frame(self) -> WalkStep:
        if self._stack:
            self._stack.pop()
        if not self._stack:
            self._current = self._done_step()
            return self._current
        parent = self._stack[-1]
        if self._return_to_branches or parent.phase == "branches":
            self._return_to_branches = False
            parent.phase = "branches"
            return self._progress()
        parent.child_index += 1
        return self._progress()

    def _enter_child(self, child_id: str, *, from_branches: bool) -> WalkStep:
        node = self._resolve(child_id)
        if from_branches:
            self._return_to_branches = True
        if isinstance(node, Collection):
            self._stack.append(_Frame(collection=node, phase="intro"))
            self._current = self._intro_step(node)
            return self._current
        if isinstance(node, Event):
            self._current = self._event_step(node)
            return self._current
        self._current = WalkStep(
            kind="event",
            title=child_id,
            body=f"Missing target “{child_id}” (not in store).",
            hint="Space — continue    Esc — exit",
            accent="#F09595",
        )
        return self._current

    def _intro_step(self, collection: Collection) -> WalkStep:
        blurb = collection.description.strip() or collection.notes.strip() or list_caption(collection)
        kids = ", ".join(self._title_of(child_id) for child_id in collection.children) or "(none)"
        body = f"{blurb}\n\nOrdered stops: {kids}"
        if collection.branches:
            body += (
                f"\n\nLater you’ll pick among {len(collection.branches)} branch(es) "
                f"on “{collection.branch_variable}” (A/B/C…)."
            )
        return WalkStep(
            kind="intro",
            title=collection.title,
            body=body,
            hint="Space — begin    Esc — exit walkthrough",
        )

    def _done_step(self) -> WalkStep:
        return WalkStep(
            kind="done",
            title="Walkthrough complete",
            body=f"Finished reviewing “{self.root.title}”.",
            hint="Space or Esc — close walkthrough",
        )

    def _event_step(self, event: Event) -> WalkStep:
        decide = next((action for action in event.actions if action.type == "decide"), None)
        if decide is not None:
            return self._event_branch_step(event, decide.raw)
        lines = [_event_blurb(event), "", f"Every {_ms(event.every_ms)} · priority {event.priority}", "", "Steps:"]
        for index, action in enumerate(event.actions, start=1):
            lines.append(f"{index}. {_action_description(action)}")
        return WalkStep(
            kind="event",
            title=event.title,
            body="\n".join(lines),
            hint="Space — next    Esc — exit walkthrough",
        )

    def _event_branch_step(self, event: Event, decide_raw: dict[str, Any]) -> WalkStep:
        variable = decide_raw.get("variable") or "signal"
        mode = decide_raw.get("mode") or "contains"
        match_a = decide_raw.get("match_a") or "A"
        explain_a = str(decide_raw.get("explain_a") or "PATH A")
        explain_b = str(decide_raw.get("explain_b") or "PATH B")
        body = (
            f"{_event_blurb(event)}\n\n"
            f"This event branches.\n"
            f"Decision: if {variable} {mode} {match_a!r} → PATH A, else → PATH B.\n\n"
            f"Press a letter to preview that path."
        )
        return WalkStep(
            kind="event_branch",
            title=event.title,
            body=body,
            hint="A / B — preview path    Esc — exit",
            choices=[
                GuideChoice(key="A", label="PATH A", detail=explain_a),
                GuideChoice(key="B", label="PATH B", detail=explain_b),
            ],
            branch_targets={
                "A": {"label": "PATH A", "explain": explain_a, "actions": list(decide_raw.get("on_a") or [])},
                "B": {"label": "PATH B", "explain": explain_b, "actions": list(decide_raw.get("on_b") or [])},
            },
            accent="#E7C36A",
        )

    def _path_preview_step(self, key: str, payload: dict[str, Any]) -> WalkStep:
        lines = [
            f"You chose {payload.get('label')} (key {key}).",
            str(payload.get("explain") or ""),
            "",
            "What this path does:",
        ]
        actions = payload.get("actions") or []
        if not actions:
            lines.append("(no actions listed)")
        for index, raw in enumerate(actions, start=1):
            if isinstance(raw, dict):
                action = Action(type=str(raw.get("type") or "?"), raw=raw)
                lines.append(f"{index}. {_action_description(action)}")
        return WalkStep(
            kind="path_preview",
            title=f"{payload.get('label')} preview",
            body="\n".join(lines),
            hint="Space — continue walkthrough    Esc — exit",
            accent="#E7C36A",
        )

    def _collection_branch_step(self, collection: Collection) -> WalkStep:
        keys = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        choices: list[GuideChoice] = []
        targets: dict[str, Any] = {}
        for index, (branch_key, child_id) in enumerate(collection.branches.items()):
            if index >= len(keys):
                break
            letter = keys[index]
            choices.append(
                GuideChoice(
                    key=letter,
                    label=f"{collection.branch_variable} = {branch_key}",
                    detail=self._title_of(child_id),
                )
            )
            targets[letter] = child_id
        body = (
            f"Branches in contention for “{collection.title}”.\n"
            f"Decided by variable “{collection.branch_variable}”.\n\n"
            f"Press a letter to walk that branch. Space skips the rest."
        )
        return WalkStep(
            kind="collection_branch",
            title=f"{collection.title} — branches",
            body=body,
            hint="A / B / C… — enter branch    Space — skip    Esc — exit",
            choices=choices,
            branch_targets=targets,
            accent="#E7C36A",
        )

    def _resolve(self, item_id: str) -> Event | Collection | None:
        if item_id in self.store.events:
            return self.store.events[item_id]
        if item_id in self.store.collections:
            return self.store.collections[item_id]
        return None

    def _title_of(self, item_id: str) -> str:
        node = self._resolve(item_id)
        if isinstance(node, (Event, Collection)):
            return node.title
        return item_id


def _ms(every_ms: int) -> str:
    if every_ms % 1000 == 0:
        return f"{every_ms // 1000}s"
    return f"{every_ms / 1000:.1f}s"
