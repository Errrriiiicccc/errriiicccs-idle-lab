"""Bridge: enabled Molecule Lab entries ↔ interactive LCO marks + hotkeys."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from idle_lab.composer.lco_placement import (
    DEFAULT_RESERVED_KEYS,
    MoleculeLcoPlacement,
    enabled_placements,
    normalize_hotkey,
    save_placement,
)
from idle_lab.live_control.molecule_marks import MoleculeMarkLayer
from idle_lab.live_control.playbook import LiveControlPlaybook
from idle_lab.models import Rect


LogFn = Callable[[str, str], None]
RunMoleculeFn = Callable[[str], None]


class MoleculeLcoBridge:
    def __init__(
        self,
        root,
        *,
        automations_root: Path,
        on_run_molecule: RunMoleculeFn | None = None,
        log: LogFn | None = None,
    ) -> None:
        self.automations_root = Path(automations_root)
        self.on_run_molecule = on_run_molecule
        self._log = log or (lambda _m, _l="info": None)
        self._placements: list[MoleculeLcoPlacement] = []
        self._rebinding_id: str | None = None
        self._show_titles = False
        self._anchor: Rect | None = None
        self._reserved: set[str] = set(DEFAULT_RESERVED_KEYS)
        self.layer = MoleculeMarkLayer(
            root,
            on_moved=self._on_moved,
            on_released=self._on_released,
            on_rebind_click=self.begin_rebind,
        )

    @property
    def rebinding(self) -> bool:
        return self._rebinding_id is not None

    def reserved_from_playbook(self, playbook: LiveControlPlaybook | None) -> set[str]:
        reserved = set(DEFAULT_RESERVED_KEYS)
        if playbook is not None:
            for token in (playbook.hotkeys or {}).values():
                key = normalize_hotkey(token)
                if key:
                    reserved.add(key)
        self._reserved = reserved
        return reserved

    def refresh(self, *, anchor: Rect | None, playbook: LiveControlPlaybook | None = None) -> list[tuple[str, str | None, str]]:
        if playbook is not None:
            self.reserved_from_playbook(playbook)
        remaps: list[tuple[str, str | None, str]] = []
        # enabled_placements already remaps + saves conflicts
        before = {p.molecule_id: p.hotkey for p in self._placements}
        self._placements = enabled_placements(self.automations_root, reserved=self._reserved)
        for place in self._placements:
            old = before.get(place.molecule_id)
            if old and place.hotkey and old != place.hotkey:
                remaps.append((place.molecule_id, old, place.hotkey))
        self._anchor = anchor
        if anchor is None:
            self.layer.clear()
            return remaps
        self.layer.sync(
            self._placements,
            anchor=anchor,
            rebinding_id=self._rebinding_id,
            show_titles=self._show_titles,
        )
        # Overlay raise_topmost on each paint; pull marks back above it.
        self.layer.raise_all()
        return remaps

    def clear(self) -> None:
        self._rebinding_id = None
        self._show_titles = False
        self._placements = []
        self.layer.clear()

    def set_show_titles(self, show: bool) -> None:
        self._show_titles = bool(show)
        self.layer.set_show_titles(self._show_titles)

    def begin_rebind(self, molecule_id: str) -> None:
        if not any(p.molecule_id == molecule_id for p in self._placements):
            return
        self._rebinding_id = molecule_id
        self._log(f"Rebind molecule “{molecule_id}” — press a key (Esc cancels).", "warn")
        if self._anchor is not None:
            self.layer.sync(
                self._placements,
                anchor=self._anchor,
                rebinding_id=self._rebinding_id,
                show_titles=self._show_titles,
            )

    def cancel_rebind(self) -> None:
        if self._rebinding_id is None:
            return
        self._log("Molecule rebind cancelled.", "info")
        self._rebinding_id = None
        if self._anchor is not None:
            self.layer.sync(
                self._placements,
                anchor=self._anchor,
                rebinding_id=None,
                show_titles=self._show_titles,
            )

    def handle_key(self, token: str, *, phase: str = "down") -> bool:
        """Return True if the key was consumed by molecule LCO (rebind or fire)."""

        key = normalize_hotkey(token)
        if key is None:
            return False
        if self._rebinding_id is not None:
            if phase != "down":
                return True
            return self._finish_rebind(key)
        if phase != "down":
            return False
        for place in self._placements:
            if normalize_hotkey(place.hotkey) == key:
                self._log(f"LCO molecule [{key}] → {place.title or place.molecule_id}", "run")
                if self.on_run_molecule is not None:
                    try:
                        self.on_run_molecule(place.molecule_id)
                    except Exception as exc:  # noqa: BLE001
                        self._log(f"Molecule run failed: {exc}", "error")
                return True
        return False

    def _finish_rebind(self, key: str) -> bool:
        target_id = self._rebinding_id
        if target_id is None:
            return True
        # Conflict with reserved playbook key or another molecule.
        owner = None
        if key in self._reserved:
            owner = f"playbook:{key}"
        for place in self._placements:
            if place.molecule_id == target_id:
                continue
            if normalize_hotkey(place.hotkey) == key:
                owner = place.molecule_id
                self.layer.flash_conflict(place.molecule_id)
                break
        if owner is not None:
            self._log(f"Key [{key}] already bound ({owner}) — pick another.", "warn")
            # Keep rebinding; flash the conflict owner if it's a molecule.
            if self._anchor is not None:
                self.layer.sync(
                    self._placements,
                    anchor=self._anchor,
                    rebinding_id=self._rebinding_id,
                    show_titles=self._show_titles,
                )
            return True
        for place in self._placements:
            if place.molecule_id == target_id:
                place.hotkey = key
                save_placement(self.automations_root, place)
                self._log(f"Bound “{place.title or place.molecule_id}” → [{key}]", "ok")
                break
        self._rebinding_id = None
        if self._anchor is not None:
            self.layer.sync(
                self._placements,
                anchor=self._anchor,
                rebinding_id=None,
                show_titles=self._show_titles,
            )
        return True

    def _on_moved(self, molecule_id: str, nx: float, ny: float) -> None:
        for place in self._placements:
            if place.molecule_id == molecule_id:
                place.nx = nx
                place.ny = ny
                break

    def _on_released(self, molecule_id: str, nx: float, ny: float) -> None:
        for place in self._placements:
            if place.molecule_id == molecule_id:
                place.nx = nx
                place.ny = ny
                save_placement(self.automations_root, place)
                self._log(
                    f"Saved LCO position for “{place.title or molecule_id}” "
                    f"({nx:.3f}, {ny:.3f})",
                    "ok",
                )
                break
