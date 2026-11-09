"""Validate automation / preset references and dry-run plans (no mouse)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.automations.schema import Collection, Event, resolve_branch
from idle_lab.automations.store import AutomationStore
from idle_lab.live_control.playbook import is_actuation_action


@dataclass
class ValidationIssue:
    level: str  # error | warn
    path: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.level == "error" for issue in self.issues)

    def add(self, level: str, path: str, message: str) -> None:
        self.issues.append(ValidationIssue(level=level, path=path, message=message))


def validate_store(store: AutomationStore, *, preset_names: set[str] | None = None) -> ValidationReport:
    report = ValidationReport()
    presets = preset_names or set()
    for roi_id, roi in store.rois.items():
        if roi.nw <= 0 or roi.nh <= 0:
            report.add("error", roi.path or roi_id, "invalid ROI size")

    for event in store.events.values():
        path = event.path or event.id
        _validate_actions(event.actions, store=store, presets=presets, path=path, report=report)

    known_ids = set(store.events) | set(store.collections)
    for collection in store.collections.values():
        path = collection.path or collection.id
        for child in collection.children:
            if child not in known_ids:
                report.add("error", path, f"unknown child id: {child}")
        for branch_key, child in collection.branches.items():
            if child not in known_ids:
                report.add("error", path, f"branch {branch_key!r} → unknown child {child}")
    return report


def _validate_actions(
    actions: list[Any],
    *,
    store: AutomationStore,
    presets: set[str],
    path: str,
    report: ValidationReport,
) -> None:
    for action in actions:
        raw = action.raw if hasattr(action, "raw") else action
        if not isinstance(raw, dict):
            report.add("error", path, "action is not an object")
            continue
        action_type = str(raw.get("type") or "")
        if action_type in {"ocr", "wait_until", "match_template"}:
            roi = raw.get("roi")
            if roi and str(roi) not in store.rois:
                # wait_until/match_template may omit roi
                if action_type == "ocr" or raw.get("roi"):
                    report.add("error", path, f"unknown roi: {roi}")
        if action_type in {"play_preset", "mouse"}:
            name = str(raw.get("preset") or raw.get("name") or "")
            if name and presets and name not in presets:
                report.add("error", path, f"unknown preset: {name}")
        if action_type == "run_event":
            event_id = str(raw.get("event") or raw.get("id") or "").strip()
            if not event_id:
                report.add("error", path, "run_event needs event id")
            elif event_id not in store.events:
                report.add("error", path, f"unknown event: {event_id}")
        if action_type == "lco":
            lco_action = str(raw.get("action") or "").strip().lower()
            if not lco_action and not str(raw.get("key") or "").strip():
                report.add("error", path, "lco needs action or key")
            elif lco_action and not is_actuation_action(lco_action):
                report.add("error", path, f"unknown lco action: {lco_action}")
        if action_type == "decide":
            for key in ("on_a", "on_b"):
                nested = raw.get(key) or []
                if isinstance(nested, list):
                    _validate_actions(nested, store=store, presets=presets, path=path, report=report)
        if action_type == "match_template":
            template = str(raw.get("template") or "")
            if not template:
                report.add("error", path, "match_template needs template id")
        if action_type == "wait_until":
            if not raw.get("variable") and not raw.get("roi") and not raw.get("check"):
                report.add("warn", path, "wait_until missing variable/roi/check")


def dry_run_event(event: Event, store: AutomationStore, *, variables: dict[str, Any] | None = None) -> list[str]:
    """Expand an event into human-readable plan lines (no side effects)."""

    lines = [f"PLAN event {event.id} ({event.title}) prio={event.priority} every_ms={event.every_ms}"]
    vars_map = dict(variables or {})
    for index, action in enumerate(event.actions):
        lines.extend(_plan_action(action.raw, index=index, store=store, variables=vars_map, indent=0))
    return lines


def dry_run_collection(
    collection: Collection,
    store: AutomationStore,
    *,
    variables: dict[str, Any] | None = None,
) -> list[str]:
    vars_map = dict(variables or {})
    lines = [
        f"PLAN collection {collection.id} ({collection.title}) "
        f"loop={collection.loop} stop_when={collection.stop_when!r}"
    ]
    branch = resolve_branch(collection, vars_map)
    if collection.branches:
        lines.append(f"  branch_variable={collection.branch_variable!r} → {branch!r}")
    order = [branch] if branch else list(collection.children)
    if branch and branch not in collection.children:
        order = [branch]
    for child_id in order:
        if child_id in store.events:
            lines.append(f"  child event {child_id}")
            for line in dry_run_event(store.events[child_id], store, variables=vars_map)[1:]:
                lines.append("  " + line)
        elif child_id in store.collections:
            nested = dry_run_collection(store.collections[child_id], store, variables=vars_map)
            for line in nested:
                lines.append("  " + line)
        else:
            lines.append(f"  MISSING child {child_id}")
    return lines


def _plan_action(
    raw: dict[str, Any],
    *,
    index: int,
    store: AutomationStore,
    variables: dict[str, Any],
    indent: int,
) -> list[str]:
    pad = "  " * (indent + 1)
    action_type = str(raw.get("type") or "?")
    desc = str(raw.get("description") or "").strip()
    head = f"{pad}[{index}] {action_type}"
    if desc:
        head += f" — {desc}"
    lines = [head]
    if action_type == "ocr":
        lines.append(f"{pad}  roi={raw.get('roi')} → var={raw.get('variable')} parse_as={raw.get('parse_as')}")
    elif action_type in {"play_preset", "mouse"}:
        lines.append(f"{pad}  preset={raw.get('preset') or raw.get('name')!r}")
    elif action_type == "run_event":
        child_id = str(raw.get("event") or raw.get("id") or "").strip()
        lines.append(f"{pad}  event={child_id!r}")
        child = store.events.get(child_id) if child_id else None
        if child is None:
            lines.append(f"{pad}  MISSING event {child_id}")
        else:
            for nested_index, nested_action in enumerate(child.actions):
                lines.extend(
                    _plan_action(
                        nested_action.raw,
                        index=nested_index,
                        store=store,
                        variables=variables,
                        indent=indent + 1,
                    )
                )
    elif action_type == "wait":
        lines.append(f"{pad}  ms={raw.get('ms') or raw.get('wait_ms')}")
    elif action_type == "wait_until":
        lines.append(
            f"{pad}  check={raw.get('check') or raw.get('variable') or raw.get('roi')} "
            f"equals={raw.get('equals')!r} timeout_ms={raw.get('timeout_ms', 5000)}"
        )
    elif action_type == "match_template":
        lines.append(
            f"{pad}  template={raw.get('template')!r} roi={raw.get('roi')!r} "
            f"threshold={raw.get('threshold', 0.85)} click={raw.get('click', False)}"
        )
    elif action_type == "decide":
        lines.append(f"{pad}  if {raw.get('variable')} {raw.get('mode', 'contains')} {raw.get('match_a')!r}")
        for label, key in (("A", "on_a"), ("B", "on_b")):
            nested = raw.get(key) or []
            lines.append(f"{pad}  PATH {label}:")
            if isinstance(nested, list):
                for nested_index, item in enumerate(nested):
                    if isinstance(item, dict):
                        lines.extend(
                            _plan_action(item, index=nested_index, store=store, variables=variables, indent=indent + 2)
                        )
    elif action_type == "set_variable":
        lines.append(f"{pad}  {raw.get('name')}={raw.get('value')!r}")
    elif action_type == "lco":
        target = raw.get("action") or f"key {raw.get('key')!r}"
        lines.append(f"{pad}  {target} ×{raw.get('times') or 1}")
    return lines


def format_report(report: ValidationReport) -> str:
    if not report.issues:
        return "validate: ok (no issues)"
    lines = [f"validate: {len(report.issues)} issue(s)"]
    for issue in report.issues:
        lines.append(f"  [{issue.level}] {issue.path}: {issue.message}")
    return "\n".join(lines)


def validate_project(root: Path, *, preset_names: set[str] | None = None) -> ValidationReport:
    store = AutomationStore(root / "automations")
    store.load_all()
    return validate_store(store, preset_names=preset_names)
