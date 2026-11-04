"""Load and validate automations JSON (ROIs, events, collections)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class AutomationSchemaError(ValueError):
    """An automations file does not match the version 1 contract."""


ACTION_TYPES = frozenset(
    {
        "screenshot",
        "ocr",
        "decide",
        "mouse",
        "play_preset",
        "record_clip",
        "csv_append",
        "log",
        "set_variable",
        "wait",
        "click",
        "detect_panel",
        "ensure_upgrade_tab",
        "seek_list_top",
    }
)


def _reject_bool(value: Any, field_name: str) -> None:
    if isinstance(value, bool):
        raise AutomationSchemaError(f"{field_name} must be a number")


def _as_float(value: Any, field_name: str) -> float:
    _reject_bool(value, field_name)
    if not isinstance(value, (int, float)):
        raise AutomationSchemaError(f"{field_name} must be a number")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise AutomationSchemaError(f"{field_name} must be finite")
    return number


def _as_int(value: Any, field_name: str, minimum: int | None = None) -> int:
    _reject_bool(value, field_name)
    if isinstance(value, float):
        if not value.is_integer():
            raise AutomationSchemaError(f"{field_name} must be a whole number")
    elif not isinstance(value, int):
        raise AutomationSchemaError(f"{field_name} must be a whole number")
    number = int(value)
    if minimum is not None and number < minimum:
        raise AutomationSchemaError(f"{field_name} must be at least {minimum}")
    return number


def _require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AutomationSchemaError(f"{field_name} is required")
    return value.strip()


@dataclass(frozen=True)
class Roi:
    id: str
    nx: float
    ny: float
    nw: float
    nh: float
    version: int = 1
    notes: str = ""
    path: str | None = None


@dataclass
class Action:
    type: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    id: str
    title: str
    priority: int
    every_ms: int
    actions: list[Action] = field(default_factory=list)
    enabled: bool = True
    version: int = 1
    description: str = ""
    notes: str = ""
    path: str | None = None


@dataclass
class Collection:
    id: str
    title: str
    children: list[str] = field(default_factory=list)
    branches: dict[str, str] = field(default_factory=dict)
    branch_variable: str = "phase"
    loop: bool = False
    stop_when: str | None = None
    version: int = 1
    description: str = ""
    notes: str = ""
    path: str | None = None


@dataclass
class RuntimeConfig:
    run_number: int = 1
    version: int = 1
    path: str | None = None


def roi_from_dict(data: Any, path: str | None = None) -> Roi:
    if not isinstance(data, dict):
        raise AutomationSchemaError("roi must be a JSON object")
    version = data.get("version", 1)
    if version != 1:
        raise AutomationSchemaError(f"unsupported roi version {version}")
    roi_id = _require_str(data.get("id"), "id")
    nx = _as_float(data.get("nx"), "nx")
    ny = _as_float(data.get("ny"), "ny")
    nw = _as_float(data.get("nw"), "nw")
    nh = _as_float(data.get("nh"), "nh")
    if nw <= 0 or nh <= 0:
        raise AutomationSchemaError("nw and nh must be positive")
    if nx < 0 or ny < 0 or nx + nw > 1.0001 or ny + nh > 1.0001:
        raise AutomationSchemaError("roi must stay within normalized [0,1] bounds")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        raise AutomationSchemaError("notes must be text")
    return Roi(id=roi_id, nx=nx, ny=ny, nw=nw, nh=nh, version=1, notes=notes, path=path)


def action_from_dict(data: Any) -> Action:
    if not isinstance(data, dict):
        raise AutomationSchemaError("action must be a JSON object")
    action_type = data.get("type")
    if action_type not in ACTION_TYPES:
        raise AutomationSchemaError(f"unknown action type: {action_type}")
    return Action(type=str(action_type), raw=dict(data))


def event_from_dict(data: Any, path: str | None = None) -> Event:
    if not isinstance(data, dict):
        raise AutomationSchemaError("event must be a JSON object")
    version = data.get("version", 1)
    if version != 1:
        raise AutomationSchemaError(f"unsupported event version {version}")
    event_id = _require_str(data.get("id"), "id")
    title = _require_str(data.get("title"), "title")
    priority = _as_int(data.get("priority", 0), "priority")
    timing = data.get("timing")
    if not isinstance(timing, dict):
        raise AutomationSchemaError("timing must be an object")
    if timing.get("type") != "interval":
        raise AutomationSchemaError("timing.type must be interval for POC")
    every_ms = _as_int(timing.get("every_ms"), "timing.every_ms", minimum=1)
    enabled = data.get("enabled", True)
    if not isinstance(enabled, bool):
        raise AutomationSchemaError("enabled must be true or false")
    raw_actions = data.get("actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise AutomationSchemaError("actions must be a non-empty list")
    actions = [action_from_dict(item) for item in raw_actions]
    description = data.get("description", "")
    if not isinstance(description, str):
        raise AutomationSchemaError("description must be text")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        raise AutomationSchemaError("notes must be text")
    return Event(
        id=event_id,
        title=title,
        priority=priority,
        every_ms=every_ms,
        actions=actions,
        enabled=enabled,
        version=1,
        description=description,
        notes=notes,
        path=path,
    )


def collection_from_dict(data: Any, path: str | None = None) -> Collection:
    if not isinstance(data, dict):
        raise AutomationSchemaError("collection must be a JSON object")
    version = data.get("version", 1)
    if version != 1:
        raise AutomationSchemaError(f"unsupported collection version {version}")
    collection_id = _require_str(data.get("id"), "id")
    title = _require_str(data.get("title"), "title")
    children = data.get("children", [])
    if not isinstance(children, list) or not all(isinstance(item, str) and item.strip() for item in children):
        raise AutomationSchemaError("children must be a list of ids")
    branches_raw = data.get("branches", {})
    if not isinstance(branches_raw, dict):
        raise AutomationSchemaError("branches must be an object")
    branches: dict[str, str] = {}
    for key, value in branches_raw.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            raise AutomationSchemaError("branches keys/values must be non-empty strings")
        branches[key] = value.strip()
    branch_variable = data.get("branch_variable", "phase")
    if not isinstance(branch_variable, str) or not branch_variable.strip():
        raise AutomationSchemaError("branch_variable must be text")
    loop = data.get("loop", False)
    if not isinstance(loop, bool):
        raise AutomationSchemaError("loop must be true or false")
    stop_when = data.get("stop_when")
    if stop_when is not None and (not isinstance(stop_when, str) or not stop_when.strip()):
        raise AutomationSchemaError("stop_when must be text or null")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise AutomationSchemaError("description must be text")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        raise AutomationSchemaError("notes must be text")
    return Collection(
        id=collection_id,
        title=title,
        children=[item.strip() for item in children],
        branches=branches,
        branch_variable=branch_variable.strip(),
        loop=loop,
        stop_when=stop_when.strip() if isinstance(stop_when, str) else None,
        version=1,
        description=description,
        notes=notes,
        path=path,
    )


def runtime_from_dict(data: Any, path: str | None = None) -> RuntimeConfig:
    if not isinstance(data, dict):
        raise AutomationSchemaError("runtime must be a JSON object")
    version = data.get("version", 1)
    if version != 1:
        raise AutomationSchemaError(f"unsupported runtime version {version}")
    run_number = _as_int(data.get("run_number", 1), "run_number", minimum=1)
    return RuntimeConfig(run_number=run_number, version=1, path=path)


def resolve_branch(collection: Collection, variables: dict[str, Any]) -> str | None:
    """Return the child id selected by branch_variable, if any."""

    if not collection.branches:
        return None
    value = variables.get(collection.branch_variable)
    if value is None:
        return None
    key = str(value).strip().lower()
    for branch_key, child_id in collection.branches.items():
        if branch_key.strip().lower() == key:
            return child_id
    return None
