"""Tower-first object map: typed UI templates + filled instances for LCO."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from idle_lab.live_control.buy_identity import (
    CatalogEntry,
    catalog_from_page_labels,
    parse_catalog,
)
from idle_lab.live_control.playbook import (
    BuySlot,
    LiveControlPlaybook,
    PlaybookError,
    RoutineMark,
    TabTarget,
)


class ObjectMapError(PlaybookError):
    """Object map file is missing or invalid."""


ALLOWED_KINDS = frozenset({"button", "tab_button", "panel", "scroll_list", "buy_button"})


@dataclass(frozen=True)
class MapObject:
    id: str
    kind: str
    label: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def parent(self) -> str | None:
        value = self.raw.get("parent")
        return str(value) if value else None

    @property
    def tab(self) -> str | None:
        value = self.raw.get("tab")
        return str(value).strip().lower() if value else None

    @property
    def hotkey_action(self) -> str | None:
        value = self.raw.get("hotkey_action")
        return str(value).strip() if value else None

    @property
    def slot_index(self) -> int | None:
        if "slot_index" not in self.raw:
            return None
        return int(self.raw["slot_index"])

    @property
    def hit(self) -> tuple[float, float] | None:
        hit = self.raw.get("hit")
        if not isinstance(hit, dict):
            return None
        return float(hit["nx"]), float(hit["ny"])

    @property
    def effects(self) -> dict[str, Any]:
        effects = self.raw.get("effects")
        return dict(effects) if isinstance(effects, dict) else {}

    @property
    def children(self) -> list[str]:
        kids = self.raw.get("children")
        if not isinstance(kids, list):
            return []
        return [str(item) for item in kids]

    def opens_panel(self) -> str | None:
        for effect in self.effects.get("ui") or []:
            if isinstance(effect, dict) and effect.get("type") == "open_panel":
                panel = effect.get("panel")
                return str(panel) if panel else None
        return None


@dataclass
class ObjectMap:
    id: str
    title: str
    surface: str
    hotkeys: dict[str, str]
    kind_templates: dict[str, dict[str, Any]]
    shared: dict[str, Any]
    objects: dict[str, MapObject]
    path: Path | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def get(self, object_id: str) -> MapObject | None:
        return self.objects.get(object_id)

    def of_kind(self, kind: str) -> list[MapObject]:
        return [obj for obj in self.objects.values() if obj.kind == kind]

    def tab_button(self, tab: str) -> MapObject | None:
        tab = tab.strip().lower()
        for obj in self.of_kind("tab_button"):
            action = obj.hotkey_action or ""
            if action == f"tab_{tab}" or obj.id.endswith(f".{tab}") or obj.label.lower() == tab:
                return obj
        return None

    def scroll_list_for_tab(self, tab: str) -> MapObject | None:
        tab = tab.strip().lower()
        for obj in self.of_kind("scroll_list"):
            if obj.tab == tab:
                return obj
        return None

    def buy_button(self, tab: str, slot_index: int) -> MapObject | None:
        """Page-1 / static slot lookup. Prefer catalog binding for live viewport identity."""

        tab = tab.strip().lower()
        for obj in self.of_kind("buy_button"):
            if obj.tab == tab and obj.slot_index == slot_index:
                return obj
        return None

    def buy_by_id(self, object_id: str) -> MapObject | None:
        obj = self.objects.get(object_id)
        if obj is None or obj.kind != "buy_button":
            return None
        return obj

    def catalog_for_tab(self, tab: str) -> list[CatalogEntry]:
        """Ordered upgrade catalog for a tab (full list when seeded; else page_labels)."""

        tab = tab.strip().lower()
        listing = self.scroll_list_for_tab(tab)
        if listing is None:
            return []
        parsed = parse_catalog(listing.raw.get("catalog"))
        if parsed:
            return parsed
        raw_labels = listing.raw.get("page_labels")
        labels = [str(item) for item in raw_labels] if isinstance(raw_labels, list) else []
        if labels:
            return catalog_from_page_labels(labels, tab=tab)
        # Last resort: buy_button objects ordered by slot_index.
        buys = sorted(
            (
                obj
                for obj in self.of_kind("buy_button")
                if obj.tab == tab and obj.slot_index is not None
            ),
            key=lambda obj: int(obj.slot_index or 0),
        )
        return [
            CatalogEntry(
                id=obj.id,
                label=obj.label,
                index=i,
                column="left" if i % 2 == 0 else "right",
            )
            for i, obj in enumerate(buys)
        ]

    def button_for_action(self, action: str) -> MapObject | None:
        for obj in self.objects.values():
            if obj.hotkey_action == action:
                return obj
        return None

    def shared_dict(self, key: str) -> dict[str, Any]:
        value = self.shared.get(key)
        return dict(value) if isinstance(value, dict) else {}

    def scroll_params(self, tab: str | None = None) -> dict[str, Any]:
        if tab:
            listing = self.scroll_list_for_tab(tab)
            if listing is not None:
                ref = listing.raw.get("scroll_ref")
                if ref:
                    params = self.shared_dict(str(ref))
                    if params:
                        return params
                embedded = listing.raw.get("scroll")
                if isinstance(embedded, dict):
                    return dict(embedded)
        return self.shared_dict("upgrade_list_scroll")

    def buy_grid(self, tab: str | None = None) -> dict[str, Any]:
        if tab:
            listing = self.scroll_list_for_tab(tab)
            if listing is not None:
                ref = listing.raw.get("grid_ref")
                if ref:
                    grid = self.shared_dict(str(ref))
                    if grid:
                        return grid
                embedded = listing.raw.get("grid")
                if isinstance(embedded, dict):
                    return dict(embedded)
        return self.shared_dict("buy_grid")

    def seek_top(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for listing in self.of_kind("scroll_list"):
            if listing.tab and listing.raw.get("seek_top"):
                out[listing.tab] = str(listing.raw["seek_top"])
        return out

    def no_retap_if_active(self, tab: str) -> bool:
        button = self.tab_button(tab)
        if button is None:
            return True
        template = self.kind_templates.get("tab_button") or {}
        rules = template.get("rules") or []
        object_rules = button.raw.get("rules") or []
        return "no_retap_if_active" in rules or "no_retap_if_active" in object_rules

    def buy_slots_for_tab(self, tab: str) -> list[BuySlot]:
        tab = tab.strip().lower()
        listing = self.scroll_list_for_tab(tab)
        grid = self.buy_grid(tab)
        cols = int(grid.get("cols") or 2)
        rows = int(grid.get("rows") or 3)
        origin_nx = float(grid.get("origin_nx") or 0.38)
        origin_ny = float(grid.get("origin_ny") or 0.735)
        col_dx = float(grid.get("col_dx") or 0.34)
        row_dy = float(grid.get("row_dy") or 0.095)
        card_nw = float(grid.get("card_nw") or 0.28)
        card_nh = float(grid.get("card_nh") or 0.09)

        labels: list[str] = []
        if listing is not None:
            raw_labels = listing.raw.get("page_labels")
            if isinstance(raw_labels, list):
                labels = [str(item) for item in raw_labels]

        buys = {
            int(obj.slot_index): obj
            for obj in self.of_kind("buy_button")
            if obj.tab == tab and obj.slot_index is not None
        }

        slots: list[BuySlot] = []
        for i in range(cols * rows):
            index = i + 1
            row, col = divmod(i, cols)
            nx = origin_nx + col * col_dx
            ny = origin_ny + row * row_dy
            buy = buys.get(index)
            if buy is not None:
                label = buy.label
                hit = buy.hit
                if hit is not None:
                    nx, ny = hit
            elif i < len(labels):
                label = labels[i]
            else:
                label = f"Buy {index}"
            slots.append(
                BuySlot(
                    index=index,
                    nx=nx,
                    ny=ny,
                    label=label,
                    card_nx=max(0.0, nx - card_nw * 0.45),
                    card_ny=max(0.0, ny - card_nh * 0.55),
                    card_nw=card_nw,
                    card_nh=card_nh,
                )
            )
        return slots

    def to_playbook(self) -> LiveControlPlaybook:
        tabs: dict[str, TabTarget] = {}
        for obj in self.of_kind("tab_button"):
            hit = obj.hit
            if hit is None:
                raise ObjectMapError(f"tab_button {obj.id} missing hit")
            action = obj.hotkey_action or ""
            tab_id = action.removeprefix("tab_") if action.startswith("tab_") else obj.id.rsplit(".", 1)[-1]
            tab_id = tab_id.strip().lower()
            tabs[tab_id] = TabTarget(id=tab_id, label=obj.label, nx=hit[0], ny=hit[1])

        buy_slots_by_tab = {tab_id: self.buy_slots_for_tab(tab_id) for tab_id in tabs}

        scroll = self.scroll_params()
        stat_obj = self.button_for_action("stat_collect")
        refresh_obj = self.button_for_action("refresh")
        stat_collect: dict[str, Any] = {"label": "Stat collect", "event": "stat_collect"}
        if stat_obj is not None:
            hit = stat_obj.hit
            if hit is not None:
                stat_collect["nx"], stat_collect["ny"] = hit
            for effect in (stat_obj.effects.get("world") or []):
                if isinstance(effect, dict) and effect.get("type") == "run_event" and effect.get("event"):
                    stat_collect["event"] = str(effect["event"])
                    break
            stat_collect["label"] = stat_obj.label
        chrome: dict[str, Any] = {}
        if refresh_obj is not None and refresh_obj.hit is not None:
            chrome["refresh_badge_nx"], chrome["refresh_badge_ny"] = refresh_obj.hit
        claim_obj = self.button_for_action("claim_gem")
        if claim_obj is not None and claim_obj.hit is not None:
            chrome["claim_badge_nx"], chrome["claim_badge_ny"] = claim_obj.hit
            chrome["claim_label"] = claim_obj.label
        routines: list[RoutineMark] = []
        for obj in self.of_kind("button"):
            action = (obj.hotkey_action or "").strip()
            if not action.startswith("routine_") or obj.hit is None:
                continue
            steps: list[str] = []
            for effect in obj.effects.get("ui") or []:
                if not isinstance(effect, dict) or effect.get("type") != "run_sequence":
                    continue
                raw_steps = effect.get("actions") or []
                if isinstance(raw_steps, list):
                    steps = [str(step).strip() for step in raw_steps if str(step).strip()]
                break
            icon = str(obj.raw.get("icon") or "▸▸").strip() or "▸▸"
            routines.append(
                RoutineMark(
                    action=action,
                    label=obj.label,
                    nx=obj.hit[0],
                    ny=obj.hit[1],
                    icon=icon,
                    steps=tuple(steps),
                )
            )

        return LiveControlPlaybook(
            id=self.id,
            title=self.title,
            surface=self.surface,
            hotkeys=dict(self.hotkeys),
            tabs=tabs,
            buy_slots_by_tab=buy_slots_by_tab,
            seek_top=self.seek_top(),
            scroll=scroll,
            stat_collect=stat_collect,
            chrome=chrome,
            routines=routines,
            path=self.path,
            raw=self.raw,
            object_map=self,
        )


def default_object_map_path(project_root: Path) -> Path:
    return Path(project_root) / "automations" / "maps" / "tower_main_gameplay.objects.json"


def load_object_map(path: Path) -> ObjectMap:
    path = Path(path)
    if not path.is_file():
        raise ObjectMapError(f"object map not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObjectMapError(f"could not read object map: {exc}") from exc
    if not isinstance(data, dict):
        raise ObjectMapError("object map must be a JSON object")
    version = data.get("version", 1)
    if version != 1:
        raise ObjectMapError(f"unsupported object map version {version}")

    hotkeys_raw = data.get("hotkeys") or {}
    if not isinstance(hotkeys_raw, dict):
        raise ObjectMapError("hotkeys must be an object")
    hotkeys = {str(k): str(v).strip().upper() for k, v in hotkeys_raw.items() if str(v).strip()}

    templates_raw = data.get("kind_templates") or {}
    if not isinstance(templates_raw, dict):
        raise ObjectMapError("kind_templates must be an object")
    kind_templates = {str(k): dict(v) for k, v in templates_raw.items() if isinstance(v, dict)}

    shared_raw = data.get("shared") or {}
    if not isinstance(shared_raw, dict):
        raise ObjectMapError("shared must be an object")
    shared = dict(shared_raw)

    objects_raw = data.get("objects")
    if not isinstance(objects_raw, list) or not objects_raw:
        raise ObjectMapError("objects must be a non-empty list")

    objects: dict[str, MapObject] = {}
    for raw in objects_raw:
        if not isinstance(raw, dict):
            raise ObjectMapError("each object must be an object")
        oid = str(raw.get("id") or "").strip()
        kind = str(raw.get("kind") or "").strip()
        if not oid:
            raise ObjectMapError("object missing id")
        if kind not in ALLOWED_KINDS:
            raise ObjectMapError(f"object {oid}: unsupported kind {kind!r}")
        if oid in objects:
            raise ObjectMapError(f"duplicate object id: {oid}")
        objects[oid] = MapObject(
            id=oid,
            kind=kind,
            label=str(raw.get("label") or oid),
            raw=dict(raw),
        )

    if not any(obj.kind == "tab_button" for obj in objects.values()):
        raise ObjectMapError("object map needs at least one tab_button")

    return ObjectMap(
        id=str(data.get("id") or path.stem),
        title=str(data.get("title") or path.stem),
        surface=str(data.get("surface") or "main_gameplay"),
        hotkeys=hotkeys,
        kind_templates=kind_templates,
        shared=shared,
        objects=objects,
        path=path,
        raw=data,
    )
