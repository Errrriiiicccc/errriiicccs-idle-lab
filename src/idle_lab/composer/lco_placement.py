"""Per-molecule LCO placement: enable, hotkey, normalized position — persists with the molecule."""

from __future__ import annotations

import json
import string
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from idle_lab.composer.expand import drafts_dir, library_path, load_library


# Keys often claimed by the Tower object-map playbook / LCO chrome.
DEFAULT_RESERVED_KEYS = frozenset(
    {
        "Q",
        "W",
        "E",
        "R",
        "F",
        "T",
        "G",
        "V",
        "C",
        "B",
        "A",
        "D",  # hold-describe
        "Y",
        "H",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    }
)

_CANDIDATE_KEYS = tuple(string.ascii_uppercase) + tuple(string.digits)


@dataclass
class MoleculeLcoPlacement:
    molecule_id: str
    title: str = ""
    enabled: bool = False
    hotkey: str | None = None
    nx: float = 0.08
    ny: float = 0.42

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.enabled),
            "hotkey": self.hotkey,
            "nx": float(self.nx),
            "ny": float(self.ny),
        }

    @classmethod
    def from_parts(
        cls,
        molecule_id: str,
        *,
        title: str = "",
        lco: dict[str, Any] | None = None,
        index: int = 0,
    ) -> MoleculeLcoPlacement:
        data = lco if isinstance(lco, dict) else {}
        nx = data.get("nx", 0.08)
        ny = data.get("ny", 0.35 + (index % 8) * 0.06)
        try:
            nx_f = float(nx)
        except (TypeError, ValueError):
            nx_f = 0.08
        try:
            ny_f = float(ny)
        except (TypeError, ValueError):
            ny_f = 0.42
        hotkey = data.get("hotkey")
        hotkey_s = str(hotkey).strip().upper() if hotkey else None
        if hotkey_s == "":
            hotkey_s = None
        return cls(
            molecule_id=str(molecule_id),
            title=str(title or molecule_id),
            enabled=bool(data.get("enabled", False)),
            hotkey=hotkey_s,
            nx=min(0.95, max(0.02, nx_f)),
            ny=min(0.95, max(0.02, ny_f)),
        )


def normalize_hotkey(token: str | None) -> str | None:
    if token is None:
        return None
    text = str(token).strip().upper()
    if len(text) != 1:
        return None
    if text not in _CANDIDATE_KEYS:
        return None
    return text


def next_free_key(taken: Iterable[str], *, reserved: Iterable[str] | None = None) -> str | None:
    blocked = {str(k).strip().upper() for k in taken if k}
    blocked |= {str(k).strip().upper() for k in (reserved or DEFAULT_RESERVED_KEYS) if k}
    for key in _CANDIDATE_KEYS:
        if key not in blocked:
            return key
    return None


def resolve_hotkey_conflicts(
    placements: list[MoleculeLcoPlacement],
    *,
    reserved: Iterable[str] | None = None,
) -> list[tuple[str, str | None, str]]:
    """Ensure enabled placements don't share keys with each other or reserved set.

    Returns list of (molecule_id, old_key, new_key) remaps performed.
    """

    reserved_set = {str(k).strip().upper() for k in (reserved or DEFAULT_RESERVED_KEYS) if k}
    remaps: list[tuple[str, str | None, str]] = []
    claimed: dict[str, str] = {}  # hotkey -> molecule_id

    for place in placements:
        if not place.enabled:
            continue
        key = normalize_hotkey(place.hotkey)
        if key is None or key in reserved_set or key in claimed:
            old = place.hotkey
            taken = set(claimed) | reserved_set
            free = next_free_key(taken, reserved=())
            if free is None:
                place.enabled = False
                place.hotkey = None
                continue
            place.hotkey = free
            remaps.append((place.molecule_id, old, free))
            claimed[free] = place.molecule_id
        else:
            place.hotkey = key
            claimed[key] = place.molecule_id
    return remaps


def load_placements(automations_root: Path) -> list[MoleculeLcoPlacement]:
    """All Lab-known molecules with their LCO blocks (enabled or not)."""

    root = Path(automations_root)
    molecules = load_library(root)
    out: list[MoleculeLcoPlacement] = []
    for i, mol in enumerate(molecules):
        mol_id = str(mol.get("id") or "").strip()
        if not mol_id:
            continue
        # Prefer draft IR lco block when present.
        lco = mol.get("lco") if isinstance(mol.get("lco"), dict) else None
        draft_path = drafts_dir(root) / f"{mol_id}.json"
        if draft_path.exists():
            try:
                draft = json.loads(draft_path.read_text(encoding="utf-8"))
                if isinstance(draft, dict) and isinstance(draft.get("lco"), dict):
                    lco = draft["lco"]
            except (OSError, json.JSONDecodeError):
                pass
        out.append(
            MoleculeLcoPlacement.from_parts(
                mol_id,
                title=str(mol.get("title") or mol_id),
                lco=lco,
                index=i,
            )
        )
    return out


def enabled_placements(automations_root: Path, *, reserved: Iterable[str] | None = None) -> list[MoleculeLcoPlacement]:
    places = [p for p in load_placements(automations_root) if p.enabled]
    remaps = resolve_hotkey_conflicts(places, reserved=reserved)
    if remaps:
        for place in places:
            save_placement(automations_root, place)
    return places


def save_placement(automations_root: Path, placement: MoleculeLcoPlacement) -> None:
    """Write LCO block onto draft (if any) and library entry for this molecule."""

    root = Path(automations_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "composer").mkdir(parents=True, exist_ok=True)
    drafts_dir(root).mkdir(parents=True, exist_ok=True)

    block = placement.to_dict()

    draft_path = drafts_dir(root) / f"{placement.molecule_id}.json"
    if draft_path.exists():
        try:
            data = json.loads(draft_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data["lco"] = block
        data.setdefault("collection_id", placement.molecule_id)
        data.setdefault("title", placement.title)
        draft_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        # Minimal draft stub so placement survives without a full compose session.
        stub = {
            "draft_id": placement.molecule_id,
            "title": placement.title,
            "collection_id": placement.molecule_id,
            "phase": "unfiled",
            "kind": "composite",
            "steps": [],
            "lco": block,
        }
        draft_path.write_text(json.dumps(stub, indent=2) + "\n", encoding="utf-8")

    lib_path = library_path(root)
    molecules: list[dict[str, Any]] = []
    if lib_path.exists():
        try:
            raw = json.loads(lib_path.read_text(encoding="utf-8"))
            items = raw.get("molecules") if isinstance(raw, dict) else None
            if isinstance(items, list):
                molecules = [m for m in items if isinstance(m, dict)]
        except (OSError, json.JSONDecodeError):
            molecules = []
    found = False
    for mol in molecules:
        if str(mol.get("id")) == placement.molecule_id:
            mol["lco"] = block
            mol.setdefault("title", placement.title)
            found = True
            break
    if not found:
        molecules.append(
            {
                "id": placement.molecule_id,
                "title": placement.title,
                "description": "LCO placement stub",
                "phase": "unfiled",
                "kind": "composite",
                "children": [],
                "lco": block,
                "source": "lab",
            }
        )
    lib_path.write_text(json.dumps({"version": 1, "molecules": molecules}, indent=2) + "\n", encoding="utf-8")


def set_enabled(
    automations_root: Path,
    molecule_id: str,
    *,
    enabled: bool,
    title: str = "",
    reserved: Iterable[str] | None = None,
) -> MoleculeLcoPlacement:
    places = load_placements(automations_root)
    place = next((p for p in places if p.molecule_id == molecule_id), None)
    if place is None:
        place = MoleculeLcoPlacement.from_parts(molecule_id, title=title or molecule_id, lco={"enabled": enabled})
    else:
        place.enabled = bool(enabled)
        if title:
            place.title = title
    if place.enabled:
        reserved_set = {str(k).strip().upper() for k in (reserved or DEFAULT_RESERVED_KEYS)}
        others = [p for p in places if p.molecule_id != molecule_id and p.enabled]
        taken = {normalize_hotkey(p.hotkey) for p in others}
        taken.discard(None)
        key = normalize_hotkey(place.hotkey)
        if key is None or key in reserved_set or key in taken:
            place.hotkey = next_free_key(set(taken) | reserved_set, reserved=())  # type: ignore[arg-type]
    save_placement(automations_root, place)
    return place
