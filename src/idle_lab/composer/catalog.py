"""Upgrade-tab capability graph sourced from the Tower object map."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from idle_lab.live_control.buy_identity import CatalogEntry
from idle_lab.live_control.objects import ObjectMap, default_object_map_path, load_object_map
from idle_lab.composer.model import SeekGuards


@dataclass(frozen=True)
class TabCapabilities:
    tab: str
    label: str
    hotkey: str
    lco_action: str
    seek_top: str | None
    catalog: tuple[CatalogEntry, ...] = ()

    def entry_for_label(self, label: str) -> CatalogEntry | None:
        want = label.strip().lower()
        for entry in self.catalog:
            if any(name.strip().lower() == want for name in entry.names):
                return entry
        return None

    def guards_for(self, entry: CatalogEntry, *, window: int = 2) -> SeekGuards:
        """Neighbor labels that mean we scrolled past the target."""

        idx = entry.index
        above = tuple(e.label for e in self.catalog[max(0, idx - window) : idx])
        below = tuple(e.label for e in self.catalog[idx + 1 : idx + 1 + window])
        return SeekGuards(too_far_up=above, too_far_down=below)


@dataclass
class CapabilityCatalog:
    """What the composer may offer, keyed by upgrade tab."""

    tabs: dict[str, TabCapabilities] = field(default_factory=dict)
    source: str = ""

    def tab_ids(self) -> list[str]:
        order = ("attack", "defense", "utility")
        known = [tab for tab in order if tab in self.tabs]
        extras = sorted(t for t in self.tabs if t not in order)
        return known + extras


def load_capability_catalog(project_root: Path, object_map: ObjectMap | None = None) -> CapabilityCatalog:
    path = default_object_map_path(project_root)
    omap = object_map if object_map is not None else load_object_map(path)
    tabs: dict[str, TabCapabilities] = {}
    hotkeys = omap.hotkeys or {}
    seek_tops = omap.seek_top()
    for tab_btn in omap.of_kind("tab_button"):
        action = tab_btn.hotkey_action or ""
        if not action.startswith("tab_"):
            continue
        tab = action[4:].strip().lower()
        if not tab:
            continue
        catalog = tuple(omap.catalog_for_tab(tab))
        tabs[tab] = TabCapabilities(
            tab=tab,
            label=tab_btn.label or tab.title(),
            hotkey=str(hotkeys.get(action) or "").upper(),
            lco_action=action,
            seek_top=seek_tops.get(tab),
            catalog=catalog,
        )
    return CapabilityCatalog(tabs=tabs, source=str(path))
