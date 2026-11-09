"""Load Live Control Overlay playbook JSON (object map or legacy flat sheet)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from idle_lab.live_control.objects import ObjectMap


class PlaybookError(ValueError):
    """Playbook file is missing or invalid."""


# Primitive actions that touch the game. ``describe`` is overlay-only and not listed.
# Routine packs use ``routine_*`` ids and are accepted by ``is_actuation_action``.
ACTUATION_ACTIONS = frozenset(
    {
        "tab_attack",
        "tab_defense",
        "tab_utility",
        *(f"buy_{i}" for i in range(1, 7)),
        "scroll_up",
        "scroll_down",
        "fling_up",
        "fling_down",
        "stat_collect",
        "claim_gem",
        "refresh",
    }
)


def is_actuation_action(action: str) -> bool:
    name = (action or "").strip().lower()
    return name in ACTUATION_ACTIONS or name.startswith("routine_")


@dataclass(frozen=True)
class RoutineMark:
    action: str
    label: str
    nx: float
    ny: float
    icon: str = "▸▸"
    steps: tuple[str, ...] = ()


@dataclass(frozen=True)
class TabTarget:
    id: str
    label: str
    nx: float
    ny: float


@dataclass(frozen=True)
class BuySlot:
    index: int  # 1-based
    nx: float
    ny: float
    label: str
    card_nx: float
    card_ny: float
    card_nw: float
    card_nh: float


@dataclass
class LiveControlPlaybook:
    id: str
    title: str
    surface: str
    hotkeys: dict[str, str]
    tabs: dict[str, TabTarget]
    buy_slots_by_tab: dict[str, list[BuySlot]]
    seek_top: dict[str, str]
    scroll: dict[str, Any]
    stat_collect: dict[str, Any]
    chrome: dict[str, Any]
    routines: list[RoutineMark] = field(default_factory=list)
    path: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    object_map: ObjectMap | None = None

    def hotkey_for(self, action_id: str) -> str | None:
        value = (self.hotkeys.get(action_id) or "").strip().upper()
        return value or None

    def action_for_token(self, token: str) -> str | None:
        needle = (token or "").strip().upper()
        if not needle:
            return None
        for action_id, key in self.hotkeys.items():
            if str(key).strip().upper() == needle:
                return action_id
        return None

    def buy_slots(self, tab: str | None) -> list[BuySlot]:
        if not tab:
            return []
        return list(self.buy_slots_by_tab.get(tab.lower(), []))


def default_playbook_path(project_root: Path) -> Path:
    """Prefer the Tower object map; fall back to the legacy flat playbook."""

    objects = Path(project_root) / "automations" / "maps" / "tower_main_gameplay.objects.json"
    if objects.is_file():
        return objects
    return Path(project_root) / "automations" / "playbooks" / "tower_main_gameplay.json"


def load_playbook(path: Path) -> LiveControlPlaybook:
    path = Path(path)
    if not path.is_file():
        raise PlaybookError(f"playbook not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlaybookError(f"could not read playbook: {exc}") from exc
    if not isinstance(data, dict):
        raise PlaybookError("playbook must be a JSON object")

    # Pointer from a thin playbook shim → object map.
    objects_map = data.get("objects_map")
    if objects_map:
        target = Path(str(objects_map))
        if not target.is_file():
            target = (path.parent / target).resolve()
        from idle_lab.live_control.objects import load_object_map

        return load_object_map(target).to_playbook()

    # Native object-map file (has objects[] + kind_templates).
    if isinstance(data.get("objects"), list) and data.get("kind_templates") is not None:
        from idle_lab.live_control.objects import load_object_map

        return load_object_map(path).to_playbook()

    return _load_legacy_flat(path, data)


def _load_legacy_flat(path: Path, data: dict[str, Any]) -> LiveControlPlaybook:
    version = data.get("version", 1)
    if version != 1:
        raise PlaybookError(f"unsupported playbook version {version}")

    hotkeys_raw = data.get("hotkeys") or {}
    if not isinstance(hotkeys_raw, dict):
        raise PlaybookError("hotkeys must be an object")
    hotkeys = {str(k): str(v).strip().upper() for k, v in hotkeys_raw.items() if str(v).strip()}

    tabs_raw = data.get("tabs") or {}
    if not isinstance(tabs_raw, dict) or not tabs_raw:
        raise PlaybookError("tabs required")
    tabs: dict[str, TabTarget] = {}
    for tab_id, raw in tabs_raw.items():
        if not isinstance(raw, dict):
            raise PlaybookError(f"tab {tab_id} must be an object")
        tid = str(tab_id).strip().lower()
        tabs[tid] = TabTarget(
            id=tid,
            label=str(raw.get("label") or tid.title()),
            nx=float(raw["nx"]),
            ny=float(raw["ny"]),
        )

    grid = data.get("buy_grid") or {}
    if not isinstance(grid, dict):
        raise PlaybookError("buy_grid must be an object")
    cols = int(grid.get("cols") or 2)
    rows = int(grid.get("rows") or 3)
    origin_nx = float(grid.get("origin_nx") or 0.38)
    origin_ny = float(grid.get("origin_ny") or 0.735)
    col_dx = float(grid.get("col_dx") or 0.34)
    row_dy = float(grid.get("row_dy") or 0.095)
    card_nw = float(grid.get("card_nw") or 0.28)
    card_nh = float(grid.get("card_nh") or 0.09)

    pages = data.get("buy_pages") or {}
    if not isinstance(pages, dict):
        raise PlaybookError("buy_pages must be an object")
    buy_slots_by_tab: dict[str, list[BuySlot]] = {}
    for tab_id, labels in pages.items():
        if not isinstance(labels, list):
            raise PlaybookError(f"buy_pages.{tab_id} must be a list")
        slots: list[BuySlot] = []
        for i in range(cols * rows):
            row, col = divmod(i, cols)
            nx = origin_nx + col * col_dx
            ny = origin_ny + row * row_dy
            label = str(labels[i]) if i < len(labels) else f"Buy {i + 1}"
            slots.append(
                BuySlot(
                    index=i + 1,
                    nx=nx,
                    ny=ny,
                    label=label,
                    card_nx=max(0.0, nx - card_nw * 0.45),
                    card_ny=max(0.0, ny - card_nh * 0.55),
                    card_nw=card_nw,
                    card_nh=card_nh,
                )
            )
        buy_slots_by_tab[str(tab_id).strip().lower()] = slots

    seek_raw = data.get("seek_top") or {}
    seek_top = {str(k).lower(): str(v) for k, v in seek_raw.items()} if isinstance(seek_raw, dict) else {}

    scroll = data.get("scroll") if isinstance(data.get("scroll"), dict) else {}
    stat = data.get("stat_collect") if isinstance(data.get("stat_collect"), dict) else {}
    chrome = data.get("chrome") if isinstance(data.get("chrome"), dict) else {}

    return LiveControlPlaybook(
        id=str(data.get("id") or path.stem),
        title=str(data.get("title") or path.stem),
        surface=str(data.get("surface") or "main_gameplay"),
        hotkeys=hotkeys,
        tabs=tabs,
        buy_slots_by_tab=buy_slots_by_tab,
        seek_top=seek_top,
        scroll=dict(scroll),
        stat_collect=dict(stat),
        chrome=dict(chrome),
        routines=[],
        path=path,
        raw=data,
        object_map=None,
    )
