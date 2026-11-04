"""Load and save preset JSON files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from idle_lab.models import TIMING_MODES, ClickPoint, Preset

class PresetError(ValueError):
    """A preset file does not match the version 1 contract."""


def project_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], here.parents[1], Path.cwd()):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def slug(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return text or "preset"


def _reject_bool(value, field: str) -> None:
    if isinstance(value, bool):
        raise PresetError(f"{field} must be a number")


def _as_float(value, field: str) -> float:
    _reject_bool(value, field)
    if not isinstance(value, (int, float)):
        raise PresetError(f"{field} must be a number")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise PresetError(f"{field} must be finite")
    return number


def _as_int(value, field: str, minimum: int) -> int:
    _reject_bool(value, field)
    if isinstance(value, float):
        if not value.is_integer():
            raise PresetError(f"{field} must be a whole number")
    elif not isinstance(value, int):
        raise PresetError(f"{field} must be a whole number")
    number = int(value)
    if number < minimum:
        raise PresetError(f"{field} must be at least {minimum}")
    return number


def preset_from_dict(data, path: str | None = None) -> Preset:
    if not isinstance(data, dict):
        raise PresetError("preset must be a JSON object")
    version = data.get("version", 1)
    if version != 1:
        raise PresetError(f"unsupported version {version}")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise PresetError("name is required")
    mode = data.get("timing_mode")
    if mode not in TIMING_MODES:
        raise PresetError("timing_mode must be instantaneous, one_second, or realtime")
    loop = data.get("loop", True)
    if not isinstance(loop, bool):
        raise PresetError("loop must be true or false")
    raw_count = data.get("loop_count", None)
    loop_count: int | None
    if raw_count is None:
        loop_count = None
    else:
        loop_count = _as_int(raw_count, "loop_count", 1)
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        raise PresetError("notes must be text")
    raw_points = data.get("points")
    if not isinstance(raw_points, list):
        raise PresetError("points must be a list")
    points: list[ClickPoint] = []
    for index, raw in enumerate(raw_points, start=1):
        if not isinstance(raw, dict):
            raise PresetError(f"point {index} must be an object")
        button = raw.get("button", "left")
        if button != "left":
            raise PresetError(f"point {index} button must be left")
        label = raw.get("label", "")
        if not isinstance(label, str):
            raise PresetError(f"point {index} label must be text")
        points.append(
            ClickPoint(
                nx=_as_float(raw.get("nx"), f"point {index} nx"),
                ny=_as_float(raw.get("ny"), f"point {index} ny"),
                delay_ms=_as_int(raw.get("delay_ms"), f"point {index} delay_ms", 0),
                hold_ms=_as_int(raw.get("hold_ms"), f"point {index} hold_ms", 1),
                button="left",
                label=label,
            )
        )
    return Preset(
        name=name.strip(),
        timing_mode=mode,
        points=points,
        loop=loop,
        loop_count=loop_count,
        notes=notes,
        version=1,
        path=path,
    )


def preset_to_dict(preset: Preset) -> dict:
    return {
        "name": preset.name,
        "version": 1,
        "timing_mode": preset.timing_mode,
        "loop": preset.loop,
        "loop_count": preset.loop_count,
        "notes": preset.notes,
        "points": [
            {
                "nx": point.nx,
                "ny": point.ny,
                "delay_ms": point.delay_ms,
                "hold_ms": point.hold_ms,
                "button": "left",
                "label": point.label,
            }
            for point in preset.points
        ],
    }


def load_preset(path: Path) -> Preset:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PresetError(f"invalid JSON ({exc.msg})") from exc
    return preset_from_dict(data, str(path))


class PresetStore:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.presets: list[Preset] = []

    def load_all(self) -> list[str]:
        presets: list[Preset] = []
        errors: list[str] = []
        for path in sorted(self.folder.glob("*.json")):
            try:
                presets.append(load_preset(path))
            except PresetError as exc:
                errors.append(f"{path.name}: {exc}")
        self.presets = presets
        return errors

    def _unique_path(self, name: str, current: str | None = None) -> Path:
        base = slug(name)
        candidate = self.folder / f"{base}.json"
        if current and Path(current) == candidate:
            return candidate
        number = 2
        while candidate.exists() and (current is None or Path(current) != candidate):
            candidate = self.folder / f"{base}-{number}.json"
            number += 1
        return candidate

    def save(self, preset: Preset) -> Preset:
        payload = json.dumps(preset_to_dict(preset), indent=2) + "\n"
        path = self._unique_path(preset.name, preset.path)
        if preset.path and Path(preset.path) != path and Path(preset.path).exists():
            Path(preset.path).unlink()
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
        preset.path = str(path)
        return preset

    def delete(self, preset: Preset) -> None:
        if preset.path and Path(preset.path).exists():
            Path(preset.path).unlink()
        self.presets = [item for item in self.presets if item.path != preset.path]
